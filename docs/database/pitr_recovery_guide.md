# PostgreSQL Point-in-Time Recovery (PITR) Documentation

## Overview

This system implements full Point-in-Time Recovery for PostgreSQL using:
- **WAL archiving** to S3-compatible object storage
- **Base backups** for fast recovery foundation
- **Automated recovery scripts** for various scenarios

## Architecture

```
PostgreSQL Primary
        │
        ├─> WAL Segments → S3 Bucket (wal_archive/)
        │
        └─> Base Backup → S3 Bucket (base_backups/) [daily]
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_BUCKET` | `postgres-wal-archive` | S3 bucket for WAL archives |
| `S3_REGION` | `us-east-1` | AWS region |
| `S3_ENDPOINT` | (empty) | Custom S3 endpoint (for MinIO, etc.) |
| `AWS_ACCESS_KEY_ID` | (required) | S3 access key |
| `AWS_SECRET_ACCESS_KEY` | (required) | S3 secret key |
| `BACKUP_RETENTION_DAYS` | `7` | Retention period for base backups |

### PostgreSQL Settings (postgresql.conf)

```conf
# Enable WAL archiving
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://postgres-wal-archive/wal_archive/%f --region us-east-1'
archive_timeout = 300  # Force WAL switch every 5 minutes

# Recovery settings (commented during normal operation)
# restore_command = 'aws s3 cp s3://postgres-wal-archive/wal_archive/%f %p'
# recovery_target_timeline = 'latest'
```

## Recovery Procedures

### Scenario 1: Full Cluster Loss

**Recovery Time Objective (RTO):** 15-30 minutes

1. Provision new PostgreSQL instance
2. Download latest base backup:
   ```bash
   aws s3 cp s3://postgres-wal-archive/base_backups/latest.tar.gz /tmp/
   tar -xzf /tmp/latest.tar.gz -C /var/lib/postgresql/data/
   ```
3. Configure `postgresql.conf` with `restore_command`
4. Start PostgreSQL: WAL replay occurs automatically
5. Verify recovery completion: `SELECT pg_is_in_recovery();` returns `false`

### Scenario 2: Point-in-Time Recovery

**Recovery to specific timestamp (e.g., before data corruption):**

```bash
# Use the recovery script
./pitr_recover.sh "2026-05-08 12:00:00"
```

The script:
- Downloads appropriate base backup
- Restores WAL segments up to target time
- Promotes database to primary

**RTO:** 5-20 minutes depending on WAL replay volume

### Scenario 3: Accidental DELETE/DROP

**Recover single table or database:**

```bash
# 1. Start recovery to time just before incident
./pitr_recover.sh "2026-05-08 10:30:00"

# 2. Dump recovered database or specific table
pg_dump -h localhost -U postgres face_recognition > recovered.sql

# 3. Stop recovery instance
pg_ctl stop -D /var/lib/postgresql/data

# 4. Restore to production
psql -h prod-db -U postgres face_recognition < recovered.sql
```

### Scenario 4: Streaming Replica Failover

If you have read replicas configured:

```sql
-- Promote replica to primary
SELECT pg_promote();

-- Or via command line
pg_ctl promote -D /var/lib/postgresql/data
```

**RTO:** < 30 seconds

## Monitoring PITR Health

### Check Archive Status

```sql
SELECT * FROM pg_stat_archiver;
```

Key metrics:
- `last_archived_wal`: Most recent WAL segment archived
- `last_failed_wal`: Last failed WAL (should be empty)
- `failed_count`: Number of failed archive attempts

### Check Replication Lag (if replicas exist)

```sql
SELECT 
    application_name,
    client_addr,
    pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn)) AS replication_lag,
    state
FROM pg_stat_replication;
```

### Verify Base Backup Exists

```bash
aws s3 ls s3://postgres-wal-archive/base_backups/ --recursive
```

## Backup Retention & Lifecycle

### S3 Lifecycle Policy (recommended)

```json
{
  "Rules": [
    {
      "Id": "DeleteOldWALs",
      "Status": "Enabled",
      "Prefix": "wal_archive/",
      "Expiration": { "Days": 30 }
    },
    {
      "Id": "DeleteOldBaseBackups",
      "Status": "Enabled",
      "Prefix": "base_backups/",
      "Expiration": { "Days": 7 }
    }
  ]
}
```

### Rotation Script

Backup rotation runs daily via cron:
```bash
0 2 * * * /var/lib/postgresql/data/rotate_backups.sh
```

## Testing Recovery

### Weekly Test (automated)

```bash
# Verify WAL archive is complete
./test_recovery.sh latest >> /var/log/pitr_weekly.log

# Check that base backup is restorable
./test_restore.sh >> /var/log/restore_weekly.log
```

### Monthly Drill (full cluster restore to test environment)

1. Restore to isolated test database
2. Run integrity checks:
   ```sql
   SELECT COUNT(*) FROM critical_tables;
   ANALYZE;
   ```
3. Verify application connectivity

## Cost Optimization

### Storage Classes
- **WAL archives**: S3 Standard-IA (infrequent access) after 30 days
- **Base backups**: S3 Glacier after 90 days (rare restores)

### Compression
WAL segments are GZIP-compressed before upload:
```bash
gzip -c $WAL_FILE | aws s3 cp - s3://bucket/$WAL_FILE.gz
```

## Troubleshooting

### WAL Archiving Stuck
```sql
-- Check archiver process
SELECT * FROM pg_stat_archiver;

-- Force WAL rotate
SELECT pg_switch_wal();

-- Verify archive_command works manually
test -x /usr/bin/aws && aws s3 cp test.wal s3://bucket/test.wal
```

### Recovery Fails with "WAL segment not found"
- Verify all WAL segments exist in S3 archive
- Check `restore_command` permissions
- Ensure IAM role has `s3:GetObject` permission

### Slow Recovery
- Monitor disk I/O during WAL replay
- Consider using provisioned IOPS for recovery instance
- Parallel WAL restore not supported natively; consider custom tooling

## Security Considerations

- **Encryption**: WAL archives encrypted at rest using S3 SSE-S3 or SSE-KMS
- **Access Control**: IAM policies restrict access to backup bucket
- **Audit Logging**: All S3 access logged to CloudTrail
- **Network**: Use VPC endpoints for S3 to avoid public internet

## Compliance

This PITR implementation supports:
- **GDPR Article 32**: Security of processing (backup & recovery)
- **SOC2**: Availability and backup procedures
- **ISO 27001**: Backup and recovery controls (A.12.3)

## Support

For issues:
1. Check `postgresql.log` for WAL archive errors
2. Verify AWS credentials: `aws sts get-caller-identity`
3. Test S3 access: `aws s3 ls s3://$S3_BUCKET/`
4. Review recovery scripts: `cat pitr_recover.sh`
