#!/bin/bash
# Docker Entrypoint - PostgreSQL initialization with pgvector
# Place in docker-entrypoint-initdb.d/
set -e

echo "=== Initializing PostgreSQL with pgvector ==="

# Create extensions
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS pgcrypto;
    CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
    CREATE EXTENSION IF NOT EXISTS btree_gist;
EOSQL

echo "Extensions created successfully"

# Set up pg_stat_statements
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE TABLE IF NOT EXISTS pg_stat_statements (
        userid oid,
        dbid oid,
        queryid bigint,
        query text,
        calls int8,
        total_time float8,
        rows int8,
        shared_blks_hit int8,
        shared_blks_read int8
    );
EOSQL

echo "pg_stat_statements table created"

# Run main schema if init.sql exists
if [ -f "/docker-entrypoint-initdb.d/01-init.sql" ]; then
    echo "Running main schema..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/01-init.sql
    echo "Main schema applied"
fi

echo "PostgreSQL initialization complete"