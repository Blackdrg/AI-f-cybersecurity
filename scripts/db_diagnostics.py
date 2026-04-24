#!/usr/bin/env python3
"""
AI-f Database Diagnostic & Repair Tool

This script performs deep database analysis including:
- Schema validation
- Data integrity checks
- Forensic audit chain verification
- Performance metrics
- Index usage analysis
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

try:
    import asyncpg
    import numpy as np
    ASYNCPG_AVAILABLE = True
except ImportError:
    print("ERROR: asyncpg not installed. Cannot run database diagnostics.")
    sys.exit(1)


class DatabaseDiagnostics:
    """Database health checker and repair tool."""
    
    def __init__(self):
        self.conn = None
        self.report = {
            'timestamp': datetime.utcnow().isoformat(),
            'connection': {},
            'schema': {},
            'integrity': {},
            'performance': {},
            'forensic': {},
            'issues': [],
            'repairs': []
        }
    
    def log(self, message: str, status: str = 'info'):
        """Print colored log message."""
        colors = {
            'pass': '\033[92m',
            'fail': '\033[91m',
            'warn': '\033[93m',
            'info': '\033[96m',
            'reset': '\033[0m'
        }
        prefix = {'pass': '✓', 'fail': '✗', 'warn': '⚠', 'info': 'ℹ'}
        print(f"{colors.get(status, '')}{prefix.get(status, '')} {message}{colors.get('reset', '')}")
        
        if status == 'fail':
            self.report['issues'].append(message)
        elif status == 'warn':
            self.report['issues'].append(f"WARNING: {message}")
    
    async def connect(self):
        """Connect to database."""
        try:
            self.conn = await asyncpg.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', 5432)),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'password'),
                database=os.getenv('DB_NAME', 'face_recognition'),
                timeout=10
            )
            self.log("Database connected successfully", 'pass')
            self.report['connection']['status'] = 'connected'
            
            version = await self.conn.fetchval('SELECT version()')
            self.report['connection']['postgresql_version'] = version
            self.log(f"PostgreSQL: {version.split()[1]}", 'info')
            
        except Exception as e:
            self.log(f"Connection failed: {e}", 'fail')
            self.report['connection']['status'] = 'failed'
            self.report['connection']['error'] = str(e)
            raise
    
    async def check_extensions(self):
        """Check required PostgreSQL extensions."""
        self.log("\nChecking Extensions...", 'info')
        
        # Check pgvector
        result = await self.conn.fetchval(
            "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'"
        )
        if result > 0:
            self.log("pgvector extension: installed", 'pass')
            self.report['schema']['pgvector'] = True
            
            # Get vector version
            version = await self.conn.fetchval("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            self.report['schema']['pgvector_version'] = version
        else:
            self.log("pgvector extension: NOT INSTALLED (required for vector search)", 'fail')
            self.report['schema']['pgvector'] = False
            self.report['issues'].append("pgvector extension missing")
    
    async def check_tables(self):
        """Verify all required tables exist."""
        self.log("\nChecking Tables...", 'info')
        
        required_tables = [
            'persons', 'embeddings', 'consent_logs', 'audit_log',
            'users', 'organizations', 'subscriptions', 'plans',
            'recognition_events', 'cameras', 'feedback',
            'model_versions', 'edge_devices', 'federated_updates'
        ]
        
        results = await self.conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        existing_tables = {r['table_name'] for r in results}
        
        missing = []
        for table in required_tables:
            if table in existing_tables:
                self.log(f"Table '{table}': exists", 'pass')
            else:
                self.log(f"Table '{table}': MISSING", 'fail')
                missing.append(table)
        
        self.report['schema']['tables_found'] = list(existing_tables)
        self.report['schema']['tables_missing'] = missing
        
        if missing:
            self.report['issues'].append(f"Missing tables: {', '.join(missing)}")
    
    async def check_indexes(self):
        """Verify critical indexes exist and are being used."""
        self.log("\nChecking Indexes...", 'info')
        
        # Check HNSW index on embeddings
        result = await self.conn.fetch("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'embeddings' 
            AND indexname LIKE '%hnsw%'
        """)
        
        if result:
            for idx in result:
                self.log(f"HNSW index '{idx['indexname']}': found", 'pass')
            self.report['schema']['hnsw_indexes'] = len(result)
        else:
            self.log("HNSW indexes: NOT FOUND (vector search will be slow)", 'fail')
            self.report['issues'].append("Missing HNSW indexes on embeddings table")
        
        # Check other indexes
        other_indexes = await self.conn.fetch("""
            SELECT COUNT(*) as count 
            FROM pg_indexes 
            WHERE tablename IN ('persons', 'recognition_events', 'audit_log')
        """)
        count = other_indexes[0]['count']
        self.log(f"Other indexes: {count} found", 'pass' if count >= 3 else 'warn')
    
    async def check_data_integrity(self):
        """Check foreign key constraints and orphaned records."""
        self.log("\nChecking Data Integrity...", 'info')
        
        # Check orphaned embeddings (no matching person)
        orphaned = await self.conn.fetchval("""
            SELECT COUNT(*) 
            FROM embeddings e 
            LEFT JOIN persons p ON e.person_id = p.person_id 
            WHERE p.person_id IS NULL
        """)
        if orphaned > 0:
            self.log(f"Orphaned embeddings: {orphaned} (should be 0)", 'warn')
            self.report['integrity']['orphaned_embeddings'] = orphaned
        else:
            self.log("No orphaned embeddings", 'pass')
        
        # Check persons without embeddings
        persons_no_emb = await self.conn.fetchval("""
            SELECT COUNT(*) 
            FROM persons p 
            LEFT JOIN embeddings e ON p.person_id = e.person_id 
            WHERE e.embedding_id IS NULL
        """)
        if persons_no_emb > 0:
            self.log(f"Persons without embeddings: {persons_no_emb}", 'info')
            self.report['integrity']['persons_no_embeddings'] = persons_no_emb
        
        # Check duplicate person IDs
        dupes = await self.conn.fetchval("""
            SELECT COUNT(*) FROM (
                SELECT person_id FROM persons 
                GROUP BY person_id HAVING COUNT(*) > 1
            ) d
        """)
        if dupes > 0:
            self.log(f"Duplicate person IDs: {dupes}", 'fail')
            self.report['issues'].append("Duplicate person IDs detected")
        else:
            self.log("No duplicate person IDs", 'pass')
    
    async def check_forensic_chain(self):
        """Verify audit log hash chain integrity."""
        self.log("\nVerifying Forensic Audit Chain...", 'info')
        
        try:
            logs = await self.conn.fetch("""
                SELECT id, action, person_id, details, previous_hash, hash 
                FROM audit_log 
                ORDER BY id ASC 
                LIMIT 1000
            """)
        except Exception as e:
            self.log(f"Cannot read audit_log: {e}", 'fail')
            return
        
        if not logs:
            self.log("Audit log empty (no activity yet)", 'info')
            self.report['forensic']['chain_valid'] = True
            return
        
        broken_links = 0
        prev_hash = None
        
        for log in logs:
            current_hash = log['hash']
            prev_hash_field = log['previous_hash']
            
            if prev_hash is None:
                # First entry should have previous_hash = '0'*64 or similar
                if prev_hash_field != '0'*64 and not prev_hash_field.startswith('0'):
                    self.log(f"Chain starts unexpectedly at ID {log['id']}", 'warn')
            elif prev_hash != prev_hash_field:
                broken_links += 1
                self.log(f"Chain broken at audit ID {log['id']}: previous_hash mismatch", 'fail')
            
            prev_hash = current_hash
        
        self.report['forensic']['audit_entries_checked'] = len(logs)
        self.report['forensic']['broken_links'] = broken_links
        
        if broken_links == 0:
            self.log(f"Audit chain verified: {len(logs)} entries intact", 'pass')
            self.report['forensic']['chain_valid'] = True
        else:
            self.log(f"Audit chain corrupted: {broken_links} broken links", 'fail')
            self.report['forensic']['chain_valid'] = False
            self.report['issues'].append("Forensic audit chain integrity compromised")
    
    async def check_performance(self):
        """Check database performance metrics."""
        self.log("\nPerformance Metrics...", 'info')
        
        # Table sizes
        sizes = await self.conn.fetch("""
            SELECT 
                relname as table_name,
                pg_size_pretty(pg_total_relation_size(relid)) as total_size,
                pg_total_relation_size(relid) as size_bytes
            FROM pg_stat_user_tables 
            ORDER BY size_bytes DESC
        """)
        
        self.report['performance']['table_sizes'] = [
            {'table': r['table_name'], 'size': r['total_size']} 
            for r in sizes[:10]
        ]
        
        for row in sizes[:5]:
            self.log(f"Table {row['table_name']}: {row['total_size']}", 'info')
        
        # Index usage
        idx_usage = await self.conn.fetch("""
            SELECT 
                indexrelname as index_name,
                idx_scan as scans,
                idx_tup_read as tuples_read,
                idx_tup_fetch as tuples_fetched
            FROM pg_stat_user_indexes 
            ORDER BY idx_scan DESC 
            LIMIT 10
        """)
        
        total_scans = sum(r['scans'] for r in idx_usage)
        self.report['performance']['total_index_scans'] = total_scans
        self.log(f"Total index scans: {total_scans}", 'info')
        
        # Connection count
        conn_count = await self.conn.fetchval("""
            SELECT COUNT(*) FROM pg_stat_activity 
            WHERE datname = current_database()
        """)
        self.report['performance']['current_connections'] = conn_count
        if conn_count > 50:
            self.log(f"High connection count: {conn_count}", 'warn')
        else:
            self.log(f"Active connections: {conn_count}", 'pass')
    
    async def check_consent_compliance(self):
        """Check GDPR/compliance data."""
        self.log("\nCompliance Data ---", 'info')
        
        # Check consent records
        consent_count = await self.conn.fetchval("SELECT COUNT(*) FROM consents")
        self.log(f"Consent records: {consent_count}", 'info')
        self.report['integrity']['consent_count'] = consent_count
        
        # Check expired consents
        expired = await self.conn.fetchval("""
            SELECT COUNT(*) FROM consents 
            WHERE expires_at < NOW()
        """)
        if expired > 0:
            self.log(f"Expired consents: {expired} (should review)", 'warn')
        
        # Check enrichment results
        enrich_count = await self.conn.fetchval("SELECT COUNT(*) FROM enrichment_results")
        self.log(f"Enrichment records: {enrich_count}", 'info')
    
    async def run_full_check(self):
        """Run all diagnostic checks."""
        print("="*60)
        print("AI-f DATABASE DIAGNOSTICS")
        print("="*60 + "\n")
        
        try:
            await self.connect()
        except Exception as e:
            print(f"\n❌ Cannot connect to database. Check connection settings.")
            return self.report
        
        await self.check_extensions()
        await self.check_tables()
        await self.check_indexes()
        await self.check_data_integrity()
        await self.check_forensic_chain()
        await self.check_performance()
        await self.check_consent_compliance()
        
        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        issues = len(self.report['issues'])
        if issues == 0:
            print("✅ All checks passed. Database is healthy.")
        else:
            print(f"⚠️  Found {issues} issue(s):")
            for issue in self.report['issues']:
                print(f"   • {issue}")
        
        print()
        return self.report
    
    async def repair_issues(self):
        """Attempt to fix common issues."""
        print("\n" + "="*60)
        print("REPAIR MODE")
        print("="*60 + "\n")
        
        if not self.conn:
            await self.connect()
        
        # Repair 1: Create missing extension
        self.log("Ensuring pgvector extension...", 'info')
        try:
            await self.conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            self.log("pgvector ensured", 'pass')
            self.report['repairs'].append("Created pgvector extension")
        except Exception as e:
            self.log(f"Failed to create pgvector: {e}", 'fail')
        
        # Repair 2: Vacuum analyze
        self.log("Running VACUUM ANALYZE...", 'info')
        try:
            await self.conn.execute("VACUUM ANALYZE;")
            self.log("VACUUM ANALYZE completed", 'pass')
            self.report['repairs'].append("Vacuumed database")
        except Exception as e:
            self.log(f"VACUUM failed: {e}", 'warn')
        
        # Repair 3: Reindex HNSW if needed
        self.log("Checking HNSW indexes...", 'info')
        result = await self.conn.fetchval("""
            SELECT COUNT(*) FROM pg_indexes 
            WHERE indexname LIKE '%hnsw%' AND tablename = 'embeddings'
        """)
        if result == 0:
            self.log("Creating HNSW indexes...", 'info')
            try:
                await self.conn.execute("""
                    CREATE INDEX IF NOT EXISTS embeddings_face_vector_idx 
                    ON embeddings USING hnsw (face_vector vector_cosine_ops) 
                    WITH (m = 32, ef_construction = 200);
                """)
                self.log("HNSW index created", 'pass')
                self.report['repairs'].append("Created HNSW index")
            except Exception as e:
                self.log(f"Index creation failed: {e}", 'fail')
        else:
            self.log(f"HNSW indexes present: {result}", 'pass')
        
        print()
        return self.report


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI-f Database Diagnostics')
    parser.add_argument('--repair', action='store_true', 
                       help='Attempt to fix common issues')
    parser.add_argument('--output', type=str, help='Save JSON report to file')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    
    args = parser.parse_args()
    
    diag = DatabaseDiagnostics()
    
    try:
        if args.repair:
            report = await diag.run_full_check()
            report = await diag.repair_issues()
        else:
            report = await diag.run_full_check()
        
        if args.output:
            import json
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"Report saved to {args.output}")
        
        if args.json:
            import json
            print(json.dumps(report, indent=2, default=str))
        
        # Exit with error code if issues found
        if len(report['issues']) > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"Diagnostics failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if diag.conn:
            await diag.conn.close()


if __name__ == '__main__':
    asyncio.run(main())
