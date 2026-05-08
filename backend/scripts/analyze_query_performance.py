#!/usr/bin/env python3
"""
Query Performance Analyzer
Compares query performance before and after index creation.
Useful for validating index effectiveness.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parent.parent / 'backend'
sys.path.insert(0, str(BACKEND_DIR))

from app.db.db_client import DBClient


class QueryPerformanceAnalyzer:
    """Analyze query performance across multiple runs."""
    
    def __init__(self, db: DBClient, iterations: int = 100):
        self.db = db
        self.iterations = iterations
        self.results: Dict[str, List[float]] = {}
    
    async def benchmark_query(self, query: str, *args) -> float:
        """Benchmark a single query, return median execution time in ms."""
        times = []
        for i in range(self.iterations):
            start = time.perf_counter()
            try:
                await self.db.fetch(query, *args)
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
            except Exception as e:
                print(f"Query failed on iteration {i}: {e}")
                return -1
        
        median = statistics.median(times)
        p95 = sorted(times)[int(len(times) * 0.95)]
        return median, p95
    
    async def compare_queries(self, queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare before/after performance for multiple queries."""
        report = {}
        
        for q in queries:
            name = q['name']
            sql = q['sql']
            params = q.get('params', ())
            print(f"\nBenchmarking: {name}")
            print(f"  Query: {sql[:100]}...")
            
            try:
                median_ms, p95_ms = await self.benchmark_query(sql, *params)
                report[name] = {
                    'median_ms': median_ms,
                    'p95_ms': p95_ms,
                    'iterations': self.iterations
                }
                print(f"  Median: {median_ms:.2f}ms, P95: {p95_ms:.2f}ms")
            except Exception as e:
                print(f"  ERROR: {e}")
                report[name] = {'error': str(e)}
        
        return report


async def main():
    """Run performance analysis."""
    print("=== Query Performance Analyzer ===")
    
    db = DBClient()
    await db.init_db()
    
    if db.pool is None:
        print("ERROR: Database not connected")
        return
    
    analyzer = QueryPerformanceAnalyzer(db, iterations=50)
    
    # Queries to benchmark (representative of critical paths)
    queries = [
        {
            'name': 'Get person by ID',
            'sql': "SELECT * FROM persons WHERE person_id = $1",
            'params': ('11111111-1111-1111-1111-111111111111',)
        },
        {
            'name': 'Get embeddings for person',
            'sql': "SELECT embedding_id FROM embeddings WHERE person_id = $1",
            'params': ('11111111-1111-1111-1111-111111111111',)
        },
        {
            'name': 'Count recognition events by camera',
            'sql': "SELECT COUNT(*) FROM recognition_events WHERE camera_id = $1 AND timestamp > $2",
            'params': ('22222222-2222-2222-2222-222222222222', '2026-01-01')
        },
        {
            'name': 'Get user by email',
            'sql': "SELECT * FROM users WHERE email = $1",
            'params': ('user@example.com',)
        },
        {
            'name': 'Get active subscriptions',
            'sql': "SELECT * FROM subscriptions WHERE user_id = $1 AND status = 'active'",
            'params': ('test_user',)
        },
        {
            'name': 'Max confidence per person (recognition analytics)',
            'sql': """
                SELECT person_id, MAX(confidence_score) as max_score 
                FROM recognition_events 
                WHERE org_id = $1 
                GROUP BY person_id
            """,
            'params': ('11111111-1111-1111-1111-111111111111',)
        }
    ]
    
    print(f"Running {len(queries)} queries × {analyzer.iterations} iterations each...")
    results = await analyzer.compare_queries(queries)
    
    print("\n=== Performance Report ===")
    print(f"{'Query':<40} {'Median (ms)':>12} {'P95 (ms)':>12}")
    print("-" * 70)
    for name, data in results.items():
        if 'error' not in data:
            print(f"{name:<40} {data['median_ms']:>12.2f} {data['p95_ms']:>12.2f}")
    
    # Recommendations
    print("\n=== Recommendations ===")
    slow_queries = [(n, d) for n, d in results.items() 
                    if 'error' not in d and d['median_ms'] > 50]
    if slow_queries:
        print("Slow queries detected (>50ms):")
        for name, data in slow_queries:
            print(f"  - {name}: {data['median_ms']:.1f}ms")
            print(f"    Consider: EXPLAIN ANALYZE, index tuning")
    else:
        print("All queries performing well (<50ms median)")
    
    await db.close()


if __name__ == '__main__':
    asyncio.run(main())
