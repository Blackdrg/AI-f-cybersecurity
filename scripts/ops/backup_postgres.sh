#!/bin/bash
# LEVI-AI Automated Database Backup
# Recommended: Run via CRON (daily at 2 AM)

BACKUP_DIR="/opt/levi-ai/backups/db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONTAINER_NAME="infra-postgres-1" # Update based on your docker-compose prefix
DB_NAME="face_recognition"
DB_USER="postgres"

mkdir -p $BACKUP_DIR

echo "Starting backup for $DB_NAME at $TIMESTAMP..."

# Perform backup using docker exec
docker exec $CONTAINER_NAME pg_dump -U $DB_USER $DB_NAME > $BACKUP_DIR/backup_$TIMESTAMP.sql

# Compress
gzip $BACKUP_DIR/backup_$TIMESTAMP.sql

# Retain only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/backup_$TIMESTAMP.sql.gz"

# Optional: Sync to S3
# aws s3 sync $BACKUP_DIR s3://your-enterprise-bucket/backups/
