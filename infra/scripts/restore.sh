#!/bin/bash
# Database restore script
# Usage: ./restore.sh <backup_file.sql.gz>

set -e

BACKUP_FILE="$1"
PG_CONTAINER="${PG_CONTAINER:-postgres}"
PG_DB="${PG_DB:-face_recognition}"
PG_USER="${PG_USER:-postgres}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo "Example: $0 ./backups/face_recognition_20250423_120000.sql.gz"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Verify checksum if available
CHECKSUM_FILE="${BACKUP_FILE}.sha256"
if [ -f "$CHECKSUM_FILE" ]; then
    echo "Verifying checksum..."
    if ! sha256sum -c "$CHECKSUM_FILE" > /dev/null 2>&1; then
        echo "ERROR: Checksum verification failed!"
        exit 1
    fi
    echo "✓ Checksum verified"
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running"
    exit 1
fi

# Check if postgres container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${PG_CONTAINER}$"; then
    echo "ERROR: PostgreSQL container '$PG_CONTAINER' is not running"
    exit 1
fi

echo "WARNING: This will overwrite the current database!"
read -p "Are you sure? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

echo "Stopping application services..."
cd "$(dirname "$0")/.."
docker compose stop backend celery-worker celery-beat

echo "Restoring database from: $BACKUP_FILE"
gunzip -c "$BACKUP_FILE" | docker exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB"

echo "✓ Restore completed"
echo "Starting application services..."
docker compose start backend celery-worker celery-beat

echo "✓ All done"
