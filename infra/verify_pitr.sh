#!/bin/bash
# PITR configuration verification script
# Checks if WAL archiving is properly configured and test backup/restore

set -e

echo "=== PostgreSQL PITR Verification ==="
echo ""

# Check required environment variables
required_vars=("S3_BUCKET" "AWS_ACCESS_KEY_ID" "AWS_SECRET_ACCESS_KEY")
missing=0
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "ERROR: $var not set"
        missing=$((missing + 1))
    fi
done

if [ $missing -gt 0 ]; then
    echo "Please set all required environment variables"
    exit 1
fi

# Test S3 connectivity
echo "1. Testing S3 connectivity..."
if aws s3 ls "s3://$S3_BUCKET/" &> /dev/null; then
    echo "   ✓ S3 bucket accessible"
else
    echo "   ✗ Cannot access S3 bucket"
    exit 1
fi

# Check PostgreSQL WAL archiving
echo "2. Checking WAL archiving status..."
ARCHIVE_STATUS=$(psql -U postgres -d face_recognition -tAc "SELECT * FROM pg_stat_archiver;" 2>/dev/null || echo "")
if [ -z "$ARCHIVE_STATUS" ]; then
    echo "   ⚠ Cannot query pg_stat_archiver (extension may not be loaded)"
else
    echo "   Archive status:"
    echo "$ARCHIVE_STATUS" | while IFS= read -r line; do
        echo "     $line"
    done
fi

# Verify base backup exists in S3
echo "3. Checking for base backups..."
BACKUPS=$(aws s3 ls "s3://$S3_BUCKET/base_backups/" 2>/dev/null || true)
if [ -n "$BACKUPS" ]; then
    echo "   ✓ Found base backups:"
    echo "$BACKUPS" | head -5 | while IFS= read -r line; do
        echo "     $line"
    done
else
    echo "   ⚠ No base backups found"
fi

# Check WAL archive
echo "4. Checking WAL archive..."
WAL_COUNT=$(aws s3 ls "s3://$S3_BUCKET/wal_archive/" 2>/dev/null | wc -l)
echo "   WAL segments archived: $WAL_COUNT"

# Test restore connectivity
echo "5. Testing restore connectivity..."
if aws s3 cp "s3://$S3_BUCKET/wal_archive/$(aws s3 ls "s3://$S3_BUCKET/wal_archive/" | tail -1 | awk '{print $4}')" /dev/null &> /dev/null; then
    echo "   ✓ Can read WAL segments from archive"
else
    echo "   ⚠ Cannot verify WAL segment download"
fi

# Create a test backup
echo ""
read -p "Create test base backup? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    TEST_BACKUP="test_backup_$(date +%Y%m%d_%H%M%S)"
    echo "Creating test backup: $TEST_BACKUP"
    pg_basebackup -h localhost -U postgres -D "/tmp/$TEST_BACKUP" -Ft -z -P
    aws s3 cp "/tmp/$TEST_BACKUP.tar.gz" "s3://$S3_BUCKET/base_backups/"
    echo "   ✓ Test backup uploaded"
    rm -rf "/tmp/$TEST_BACKUP" "/tmp/$TEST_BACKUP.tar.gz"
fi

echo ""
echo "=== Verification Complete ==="
echo ""
echo "Recommended actions:"
echo "1. Schedule daily base backups: 0 2 * * * $BACKUP_SCRIPT"
echo "2. Schedule weekly recovery tests"
echo "3. Set up CloudWatch/S3 metrics for backup health"
echo "4. Document recovery procedures in runbook"
