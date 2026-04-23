#!/bin/bash
# Daily PostgreSQL Backup Script
# Place in infra/scripts/backup.sh and set up cron or systemd timer

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/face_recognition_$TIMESTAMP.sql.gz"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
PG_CONTAINER="${PG_CONTAINER:-postgres}"
PG_DB="${PG_DB:-face_recognition}"
PG_USER="${PG_USER:-postgres}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✓ $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ✗ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠ $1${NC}"
}

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running"
    exit 1
fi

# Check if postgres container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${PG_CONTAINER}$"; then
    log_error "PostgreSQL container '$PG_CONTAINER' is not running"
    exit 1
fi

log "Starting backup of database: $PG_DB"

# Perform backup using pg_dump inside container
if docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" --format=plain 2>/dev/null | gzip > "$BACKUP_FILE"; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_success "Backup created successfully: $BACKUP_FILE (size: $BACKUP_SIZE)"
    
    # Create checksum
    sha256sum "$BACKUP_FILE" > "${BACKUP_FILE}.sha256"
    log "Checksum saved: ${BACKUP_FILE}.sha256"
    
    # Upload to S3 if configured (optional)
    if [ -n "$AWS_S3_BUCKET" ] && command -v aws &> /dev/null; then
        log "Uploading to S3 bucket: $AWS_S3_BUCKET"
        aws s3 cp "$BACKUP_FILE" "s3://$AWS_S3_BUCKET/backups/"
        aws s3 cp "${BACKUP_FILE}.sha256" "s3://$AWS_S3_BUCKET/backups/"
        log_success "Uploaded to S3"
    fi
    
    # Clean up old backups
    log "Cleaning up backups older than $RETENTION_DAYS days"
    find "$BACKUP_DIR" -name "*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "*.sha256" -type f -mtime +$RETENTION_DAYS -delete
    log "Old backups cleaned up"
    
    # Report success
    ls -lh "$BACKUP_DIR" | tail -5
    
    exit 0
else
    log_error "Backup failed"
    exit 1
fi
