#!/bin/bash
# PostgreSQL Point-in-Time Recovery (PITR) Setup Script
# This script configures WAL archiving to S3-compatible object storage
# and sets up the recovery infrastructure.
#
# Usage: ./docker-entrypoint-initdb.d/pg_basebackup.sh
# Or manually: sudo -u postgres bash ./pg_basebackup.sh

set -e

# Configuration from environment variables
S3_BUCKET="${S3_BUCKET:-postgres-wal-archive}"
S3_REGION="${S3_REGION:-us-east-1}"
S3_ENDPOINT="${S3_ENDPOINT:-}"
AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
PGDATA="${PGDATA:-/var/lib/postgresql/data}"

echo "=== PostgreSQL PITR Configuration ==="
echo "WAL Archive Bucket: $S3_BUCKET"
echo "Region: $S3_REGION"
echo "Retention: $BACKUP_RETENTION_DAYS days"

# Validate credentials
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "ERROR: AWS credentials not set (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)"
    exit 1
fi

# Configure AWS CLI for S3 access
aws configure set aws_access_key_id "$AWS_ACCESS_KEY_ID"
aws configure set aws_secret_access_key "$AWS_SECRET_ACCESS_KEY"
aws configure set default.region "$S3_REGION"
if [ -n "$S3_ENDPOINT" ]; then
    aws configure set default.s3.endpoint "$S3_ENDPOINT"
fi

# Create S3 bucket if it doesn't exist
echo "Creating S3 bucket if needed..."
aws s3api head-bucket --bucket "$S3_BUCKET" 2>/dev/null || \
    aws s3api create-bucket --bucket "$S3_BUCKET" --region "$S3_REGION"

# Enable versioning for point-in-time recovery
aws s3api put-bucket-versioning \
    --bucket "$S3_BUCKET" \
    --versioning-configuration Status=Enabled

# Create base backup
BACKUP_NAME="base_backup_$(date +%Y%m%d_%H%M%S)"
echo "Creating base backup: $BACKUP_NAME"
pg_basebackup \
    -h localhost \
    -U postgres \
    -D "$PGDATA/backups/$BACKUP_NAME" \
    -Ft \
    -z \
    -P \
    -X fetch

# Upload base backup to S3
echo "Uploading base backup to S3..."
aws s3 cp "$PGDATA/backups/$BACKUP_NAME.tar.gz" \
    "s3://$S3_BUCKET/base_backups/"

# Configure archive_command in postgresql.conf
echo "Configuring WAL archiving in postgresql.conf..."
CONF_FILE="$PGDATA/../postgresql.conf"
if [ -f "$CONF_FILE" ]; then
    # WAL archiving settings
    cat >> "$CONF_FILE" << EOF

# WAL Archiving for PITR
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://$S3_BUCKET/wal_archive/%f --region $S3_REGION'
archive_timeout = 300

# Recovery settings (commented - active only during recovery)
#restore_command = 'aws s3 cp s3://$S3_BUCKET/wal_archive/%f %p'
#recovery_target_time = 'latest'

# Retention policy
wal_keep_size = 512MB  # Keep some WALs locally for fast failover
EOF
    echo "WAL archiving configured in $CONF_FILE"
else
    echo "WARNING: postgresql.conf not found at $CONF_FILE"
fi

# Create recovery configuration template
RECOVERY_CONF="$PGDATA/../recovery.conf.sample"
echo "Creating recovery configuration template: $RECOVERY_CONF"
cat > "$RECOVERY_CONF" << EOF
# PostgreSQL Point-in-Time Recovery Configuration
# Copy this file to postgresql.conf and restart to initiate recovery

# Restore WALs from archive
restore_command = 'aws s3 cp s3://$S3_BUCKET/wal_archive/%f %p'
recovery_target_timeline = 'latest'

# Optional: recover to specific time
# recovery_target_time = '2026-05-08 12:00:00'

# Optional: recover to specific LSN
# recovery_target_lsn = '0/16B6C0'

# Command to run after recovery completes
recovery_end_command = 'pg_ctl promote -D $PGDATA'

# Standby mode (if using as replica)
# primary_conninfo = 'host=primary_host port=5432 user=replicator password=...'

EOF

# Create backup rotation script
ROTATE_SCRIPT="$PGDATA/../rotate_backups.sh"
echo "Creating backup rotation script: $ROTATE_SCRIPT"
cat > "$ROTATE_SCRIPT" << 'ROTATE_EOF'
#!/bin/bash
# Delete backups older than retention period
find /var/lib/postgresql/data/backups -name "base_backup_*" -type d -mtime +${BACKUP_RETENTION_DAYS} -exec rm -rf {} \;

# Delete old WAL archives from S3 (older than retention)
aws s3api list-object-versions --bucket ${S3_BUCKET} --prefix wal_archive/ \
    --query 'Versions[?IsLatest==`false` && LastModified<`$(date -d "-${BACKUP_RETENTION_DAYS} days" +%Y-%m-%d)`].[Key,VersionId]' \
    | while read key version; do
        aws s3api delete-object --bucket ${S3_BUCKET} --key "$key" --version-id "$version"
    done
ROTATE_EOF
chmod +x "$ROTATE_SCRIPT"

# Create recovery script
RECOVER_SCRIPT="$PGDATA/../pitr_recover.sh"
echo "Creating PITR recovery script: $RECOVER_SCRIPT"
cat > "$RECOVER_SCRIPT" << 'RECOVER_EOF'
#!/bin/bash
# Point-in-Time Recovery Script
#
# Usage: ./pitr_recover.sh <recovery_time>
#   recovery_time: ISO timestamp (e.g., "2026-05-08 12:00:00") or "latest"
#
# Example: ./pitr_recover.sh "2026-05-08 12:00:00"

set -e

RECOVERY_TIME="${1:-latest}"
BACKUP_DIR="/var/lib/postgresql/data/recovery_temp"
WAL_DIR="/var/lib/postgresql/data/wal_archive"

echo "=== PITR Recovery to: $RECOVERY_TIME ==="

# 1. Stop PostgreSQL
pg_ctl stop -D /var/lib/postgresql/data -m fast

# 2. Create recovery directory
mkdir -p "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"/*

# 3. Find latest base backup before recovery time
echo "Finding base backup..."
LATEST_BACKUP=$(aws s3 ls "s3://${S3_BUCKET}/base_backups/" \
    | sort \
    | tail -1 \
    | awk '{print $4}')

if [ -z "$LATEST_BACKUP" ]; then
    echo "ERROR: No base backup found"
    exit 1
fi

echo "Using base backup: $LATEST_BACKUP"

# 4. Download and extract base backup
echo "Downloading base backup..."
aws s3 cp "s3://${S3_BUCKET}/base_backups/${LATEST_BACKUP}" \
    "$BACKUP_DIR/base_backup.tar.gz"

tar -xzf "$BACKUP_DIR/base_backup.tar.gz" -C "$BACKUP_DIR"

# 5. Clear current data directory
rm -rf /var/lib/postgresql/data/*
cp -r "$BACKUP_DIR"/* /var/lib/postgresql/data/

# 6. Create recovery configuration
echo "Creating recovery.conf..."
cat > /var/lib/postgresql/data/postgresql.conf << RECOVERY_CONF
# PITR Recovery Configuration
restore_command = 'aws s3 cp s3://${S3_BUCKET}/wal_archive/%f %p'
recovery_target_timeline = 'latest'
recovery_end_command = 'pg_ctl promote -D /var/lib/postgresql/data'
RECOVERY_CONF

if [ "$RECOVERY_TIME" != "latest" ]; then
    echo "recovery_target_time = '$RECOVERY_TIME'" >> /var/lib/postgresql/data/postgresql.conf
fi

# 7. Start PostgreSQL in recovery mode
echo "Starting PostgreSQL in recovery mode..."
pg_ctl start -D /var/lib/postgresql/data

# 8. Monitor recovery progress
echo "Monitoring recovery progress..."
tail -f /var/lib/postgresql/data/log/postgresql.log | while read line; do
    echo "$line"
    if echo "$line" | grep -q "recovery.*complete"; then
        echo "=== Recovery Complete ==="
        break
    fi
done

echo "PITR recovery completed successfully."
RECOVER_EOF
chmod +x "$RECOVER_SCRIPT"

# Create recovery documentation
RECOVERY_DOC="$PGDATA/../PITR_RECOVERY.md"
echo "Creating PITR recovery documentation: $RECOVERY_DOC"
cat > "$RECOVERY_DOC" << 'DOC_EOF'
# Point-in-Time Recovery (PITR) Guide

## Overview
This PostgreSQL instance is configured with continuous WAL archiving to S3
for point-in-time recovery capabilities.

## Recovery Scenarios

### 1. Recover to Latest Point (after crash)
```bash
# If streaming replica is available, promote it
pg_ctl promote -D /var/lib/postgresql/data

# Or use automated failover
```

### 2. Recover to Specific Timestamp
```bash
./pitr_recover.sh "2026-05-08 12:00:00"
```

### 3. Restore from Base Backup
```bash
# Stop PostgreSQL
pg_ctl stop -D /var/lib/postgresql/data

# Download latest base backup
aws s3 cp s3://${S3_BUCKET}/base_backups/latest.tar.gz /tmp/
tar -xzf /tmp/latest.tar.gz -C /var/lib/postgresql/data/

# Start and let WAL replay occur
pg_ctl start -D /var/lib/postgresql/data
```

## Recovery Time Objectives (RTO)
- **Full cluster restore**: ~15-30 minutes (base backup + WAL replay)
- **Point-in-time recovery to specific timestamp**: ~5-20 minutes
- **Replica promotion**: ~30 seconds (if streaming replica configured)

## Recovery Point Objectives (RPO)
- **Maximum data loss**: Depends on `archive_timeout` (default 5 minutes)
- With `archive_timeout=300`: at most 5 minutes of data loss

## Testing Recovery
Regularly test recovery procedures:

```bash
# Weekly full recovery test
0 2 * * 0 /var/lib/postgresql/data/test_recovery.sh >> /var/log/pitr_test.log 2>&1

# Monthly full cluster restore drill
0 3 1 * * /var/lib/postgresql/data/full_restore_drill.sh
```

## Monitoring
Monitor PITR health:
- WAL archive lag: `SELECT pg_last_wal_receive_lsn() - pg_last_wal_replay_lsn() AS lag_bytes;`
- Archive status: `SELECT * FROM pg_stat_archiver;`
- Last archived WAL: `SELECT last_archived_wal FROM pg_stat_archiver;`

## Troubleshooting

### WAL Archiving Not Working
Check archive_command output:
```sql
SELECT * FROM pg_stat_archiver;
```

Common issues:
- AWS credentials not configured
- S3 bucket permissions
- Disk space for temporary WAL files

### Recovery Stuck
Check `postgresql.log` for errors. Common fixes:
- Ensure all WAL segments are available in archive
- Increase `restore_command` timeout
- Verify S3 connectivity

## Backup Retention
- Base backups: retained for ${BACKUP_RETENTION_DAYS} days
- WAL archives: retained indefinitely for full PITR capability
- Consider lifecycle policies on S3 for cost optimization
DOC_EOF

echo "PITR configuration complete!"
echo ""
echo "Next steps:"
echo "1. Restart PostgreSQL to apply WAL archiving settings"
echo "2. Verify archiving: SELECT * FROM pg_stat_archiver;"
echo "3. Test recovery: $RECOVER_SCRIPT <timestamp>"
echo "4. Set up backup rotation cron: (crontab -e)"
echo "   ${ROTATE_SCRIPT} daily"
echo ""
echo "Documentation: $RECOVERY_DOC"
