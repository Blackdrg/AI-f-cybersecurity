#!/bin/bash
# AI-F Database Restore Script
# Restores PostgreSQL database from a backup file
# Usage: ./restore.sh <backup_file.sql> [database_name]

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_header() {
    echo -e "${CYAN}=== $1 ===${NC}"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}! $1${NC}"
}

# Check prerequisites
log_header "Checking Prerequisites"

if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed."
    exit 1
fi

if [ -z "$1" ]; then
    log_error "No backup file specified."
    echo "Usage: ./restore.sh <backup_file.sql> [database_name]"
    echo "Example: ./restore.sh backups/backup_2026-05-06.sql"
    exit 1
fi

BACKUP_FILE="$1"
DB_NAME="${2:-ai_f_recognition}"

if [ ! -f "$BACKUP_FILE" ]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

log_success "Backup file found: $BACKUP_FILE"
log_success "Target database: $DB_NAME"

# Check if PostgreSQL container is running
log_header "Checking PostgreSQL Container"

CONTAINER_NAME=$(docker ps --filter "name=postgres" --format "table {{.Names}}" | tail -n +2 | head -1)

if [ -z "$CONTAINER_NAME" ]; then
    log_error "PostgreSQL container is not running."
    echo "Start it with: cd infra && docker-compose up -d postgres"
    exit 1
fi

log_success "Found container: $CONTAINER_NAME"

# Verify container is accessible
log_header "Verifying Database Access"

if ! docker exec "$CONTAINER_NAME" pg_isready -U postgres &> /dev/null; then
    log_error "PostgreSQL is not ready in the container."
    exit 1
fi

log_success "PostgreSQL is ready"

# Confirm restore
echo
log_warning "WARNING: This will overwrite the database '$DB_NAME' with data from $BACKUP_FILE"
read -p "Are you sure you want to continue? (yes/no): " -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    log_warning "Restore cancelled."
    exit 0
fi

# Stop the backend to prevent writes during restore
log_header "Stopping Backend Services"

cd infra || true

if docker ps --filter "name=backend" --format "table {{.Names}}" | grep -q backend; then
    log_warning "Stopping backend container temporarily..."
    docker-compose stop backend || true
    log_success "Backend stopped"
else
    log_success "Backend container not running (OK)"
fi

cd ..

# Perform restore
log_header "Restoring Database"

# Drop and recreate database
log_warning "Dropping existing database..."
docker exec "$CONTAINER_NAME" psql -U postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true

log_success "Creating fresh database..."
docker exec "$CONTAINER_NAME" psql -U postgres -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || {
    log_error "Failed to create database"
    exit 1
}

# Restore from backup
log_warning "Restoring from backup..."
if docker exec -i "$CONTAINER_NAME" psql -U postgres -d "$DB_NAME" < "$BACKUP_FILE" 2>/dev/null; then
    log_success "Database restored successfully"
else
    log_error "Restore failed. Check backup file format."
    # Try to restart backend
    cd infra && docker-compose start backend 2>/dev/null || true
    cd ..
    exit 1
fi

# Verify restore
log_header "Verifying Restore"

TABLES=$(docker exec "$CONTAINER_NAME" psql -U postgres -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d '[:space:]')

if [ "$TABLES" -gt 0 ]; then
    log_success "Verified: $TABLES tables restored"
else
    log_warning "No tables found in restored database"
fi

# Restart backend
log_header "Restarting Backend"

cd infra || true
if docker-compose ps backend | grep -q "Up"; then
    log_warning "Starting backend container..."
    docker-compose start backend
    log_success "Backend started"
else
    log_success "Backend was not running previously"
fi

cd ..

# Summary
log_header "Restore Complete"

cat << EOF
${GREEN}Database restored successfully!${NC}

Backup file: $BACKUP_FILE
Database:   $DB_NAME
Container:  $CONTAINER_NAME

Next steps:
  1. Verify application connectivity: curl http://localhost:8000/api/health
  2. Check logs: docker logs $CONTAINER_NAME
  3. Run migrations if needed: pytest backend/tests/

To create a new backup:
  pg_dump -h localhost -U postgres $DB_NAME > backups/manual_$(date +%Y-%m-%d_%H%M%S).sql

EOF

log_success "Restore operation completed successfully"
