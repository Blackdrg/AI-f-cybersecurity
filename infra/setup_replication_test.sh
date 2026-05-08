#!/bin/bash
# Setup script for local replication test environment
# Creates a primary and replica PostgreSQL instance for testing

set -e

echo "=== Setting up local PostgreSQL replication test environment ==="

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker not found. Please install Docker first."
    exit 1
fi

# Create network for replication
NETWORK_NAME="postgres-replication-test"
docker network create $NETWORK_NAME 2>/dev/null || true

# Stop any existing containers
echo "Cleaning up existing containers..."
docker rm -f pg-primary pg-replica 2>/dev/null || true

# Generate random passwords
PRIMARY_PASSWORD=$(openssl rand -base64 12)
REPL_PASSWORD=$(openssl rand -base64 12)

echo "Primary password: $PRIMARY_PASSWORD"
echo "Replica password: $REPL_PASSWORD"

# Start primary
echo "Starting primary PostgreSQL..."
docker run -d \
    --name pg-primary \
    --network $NETWORK_NAME \
    -e POSTGRES_PASSWORD=$PRIMARY_PASSWORD \
    -e POSTGRES_DB=face_recognition \
    -e PGUSER=postgres \
    -e PGPASSWORD=$PRIMARY_PASSWORD \
    -p 5432:5432 \
    pgvector/pgvector:pg15 \
    -c wal_level=replica \
    -c max_wal_senders=10 \
    -c wal_log_hints=on \
    -c max_replication_slots=10

# Wait for primary to be ready
echo "Waiting for primary to be ready..."
for i in {1..30}; do
    if docker exec pg-primary pg_isready -U postgres &> /dev/null; then
        echo "Primary ready!"
        break
    fi
    sleep 2
    if [ $i -eq 30 ]; then
        echo "ERROR: Primary did not start in time"
        exit 1
    fi
done

# Create replication user on primary
echo "Creating replication user..."
docker exec pg-primary psql -U postgres -c "
CREATE USER replicator WITH REPLICATION PASSWORD '$REPL_PASSWORD';
GRANT rds_replication TO replicator;
" || true

# Start replica
echo "Starting replica PostgreSQL..."
docker run -d \
    --name pg-replica \
    --network $NETWORK_NAME \
    -e POSTGRES_PASSWORD=$REPL_PASSWORD \
    -e POSTGRES_DB=face_recognition \
    -e PGUSER=postgres \
    -e PGPASSWORD=$REPL_PASSWORD \
    -p 5433:5432 \
    pgvector/pgvector:pg15 \
    -c hot_standby=on

# Wait for replica to be ready
echo "Waiting for replica to be ready..."
for i in {1..30}; do
    if docker exec pg-replica pg_isready -U postgres &> /dev/null; then
        echo "Replica ready!"
        break
    fi
    sleep 2
    if [ $i -eq 30 ]; then
        echo "ERROR: Replica did not start in time"
        exit 1
    fi
done

# Configure replication on replica
echo "Configuring replication on replica..."
docker exec pg-replica bash -c "
cat > /var/lib/postgresql/data/postgresql.conf << EOF
primary_conninfo = 'host=pg-primary port=5432 user=replicator password=\"$REPL_PASSWORD\" dbname=face_recognition'
primary_slot_name = 'replication_slot'
restore_command = 'cp /var/lib/postgresql/data/wal_archive/%f %p'
archive_cleanup_command = 'pg_archivecleanup /var/lib/postgresql/data/wal_archive %r'
EOF

# Restart replica to apply settings
pg_ctl stop -D /var/lib/postgresql/data -m fast
pg_ctl start -D /var/lib/postgresql/data
"

echo ""
echo "=== Replication test environment ready ==="
echo ""
echo "Connection strings:"
echo "  Primary:   postgresql://postgres:$PRIMARY_PASSWORD@localhost:5432/face_recognition"
echo "  Replica:   postgresql://postgres:$REPL_PASSWORD@localhost:5433/face_recognition"
echo ""
echo "To run replication tests:"
echo "  export DB_HOST=localhost"
echo "  export DB_PORT=5432"
echo "  export DB_PASSWORD=$PRIMARY_PASSWORD"
echo "  export DB_READ_REPLICAS=localhost:5433"
echo "  pytest backend/tests/integration/test_replication.py -v"
echo ""
echo "To tear down:"
echo "  docker rm -f pg-primary pg-replica"
echo "  docker network rm $NETWORK_NAME"
