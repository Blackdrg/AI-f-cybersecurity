#!/usr/bin/env python3
"""
AI-f System Diagnostic Suite

This script performs comprehensive system health checks and generates
a detailed diagnostic report for troubleshooting and maintenance.

Usage:
    python diagnostics.py [--json] [--output report.txt]

Options:
    --json       Output in JSON format (default: human-readable)
    --output     Save report to file
    --quick      Skip heavy checks (model loading, GPU tests)
"""

import asyncio
import sys
import os
import json
import time
import socket
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class Color:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


class SystemDiagnostics:
    """Comprehensive system diagnostics for AI-f."""
    
    def __init__(self, output_json: bool = False, quick: bool = False):
        self.results: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat(),
            'system': {},
            'services': {},
            'models': {},
            'database': {},
            'cache': {},
            'vector_store': {},
            'gpu': {},
            'network': {},
            'issues': [],
            'warnings': [],
            'passed': []
        }
        self.output_json = output_json
        self.quick = quick
    
    def log(self, message: str, status: str = 'info'):
        """Log a message with color coding."""
        colors = {
            'pass': Color.GREEN,
            'fail': Color.RED,
            'warn': Color.YELLOW,
            'info': Color.CYAN
        }
        prefix = {
            'pass': '✅',
            'fail': '❌',
            'warn': '⚠️',
            'info': 'ℹ️'
        }
        color = colors.get(status, Color.END)
        print(f"{color}{prefix.get(status, '')} {message}{Color.END}")
        
        # Store result
        if status == 'pass':
            self.results['passed'].append(message)
        elif status == 'fail':
            self.results['issues'].append(message)
        elif status == 'warn':
            self.results['warnings'].append(message)
    
    def check_system_resources(self):
        """Check CPU, memory, disk usage."""
        self.log("System Resources", 'info')
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        self.results['system']['cpu'] = {
            'percent': cpu_percent,
            'cores': cpu_count
        }
        if cpu_percent > 90:
            self.log(f"High CPU usage: {cpu_percent}%", 'warn')
        else:
            self.log(f"CPU: {cpu_percent}% used, {cpu_count} cores", 'pass')
        
        # Memory
        memory = psutil.virtual_memory()
        self.results['system']['memory'] = {
            'total_gb': round(memory.total / (1024**3), 2),
            'available_gb': round(memory.available / (1024**3), 2),
            'percent': memory.percent
        }
        if memory.percent > 85:
            self.log(f"High memory usage: {memory.percent}%", 'warn')
        else:
            self.log(f"Memory: {memory.percent}% used", 'pass')
        
        # Disk
        disk = psutil.disk_usage('/')
        self.results['system']['disk'] = {
            'total_gb': round(disk.total / (1024**3), 2),
            'free_gb': round(disk.free / (1024**3), 2),
            'percent': disk.percent
        }
        if disk.percent > 90:
            self.log(f"Low disk space: {disk.percent}% used", 'warn')
        else:
            self.log(f"Disk: {disk.percent}% used", 'pass')
    
    async def check_database(self):
        """Check PostgreSQL connectivity and performance."""
        self.log("Database Connectivity", 'info')
        
        if not ASYNCPG_AVAILABLE:
            self.log("asyncpg not installed - database checks skipped", 'warn')
            self.results['database']['available'] = False
            return
        
        try:
            # Try to connect (use env vars or defaults)
            conn = await asyncpg.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', 5432)),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'password'),
                database=os.getenv('DB_NAME', 'face_recognition'),
                timeout=5
            )
            
            # Check connection
            version = await conn.fetchval('SELECT version()')
            self.results['database']['connected'] = True
            self.results['database']['version'] = version
            self.log(f"Connected to PostgreSQL: {version[:20]}", 'pass')
            
            # Check pgvector
            try:
                await conn.execute('CREATE EXTENSION IF NOT EXISTS vector;')
                self.log("pgvector extension available", 'pass')
                self.results['database']['pgvector'] = True
            except Exception as e:
                self.log(f"pgvector extension issue: {e}", 'warn')
                self.results['database']['pgvector'] = False
            
            # Check table counts
            tables = ['persons', 'embeddings', 'audit_log', 'users', 'organizations']
            counts = {}
            for table in tables:
                try:
                    count = await conn.fetchval(f'SELECT COUNT(*) FROM {table}')
                    counts[table] = count
                except:
                    counts[table] = 0
            
            self.results['database']['table_counts'] = counts
            self.log(f"Table counts: {counts}", 'info')
            
            # Check connections
            active_conn = await conn.fetchval(
                "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = $1",
                os.getenv('DB_NAME', 'face_recognition')
            )
            self.results['database']['active_connections'] = active_conn
            if active_conn > 50:
                self.log(f"High connection count: {active_conn}", 'warn')
            
            await conn.close()
            
        except Exception as e:
            self.results['database']['connected'] = False
            self.results['database']['error'] = str(e)
            self.log(f"Database connection failed: {e}", 'fail')
    
    async def check_redis(self):
        """Check Redis connectivity."""
        self.log("Redis Cache", 'info')
        
        if not REDIS_AVAILABLE:
            self.log("redis-py not installed - Redis checks skipped", 'warn')
            return
        
        try:
            r = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                decode_responses=True,
                socket_timeout=5
            )
            
            # Ping
            pong = r.ping()
            if pong:
                self.log("Redis responding to ping", 'pass')
                self.results['cache']['available'] = True
                
                # Info
                info = r.info()
                self.results['cache']['version'] = info.get('redis_version')
                self.results['cache']['used_memory_mb'] = round(info.get('used_memory', 0) / (1024**2), 2)
                self.results['cache']['connected_clients'] = info.get('connected_clients', 0)
                
                self.log(f"Redis {info.get('redis_version')} - {self.results['cache']['used_memory_mb']}MB used", 'info')
            else:
                self.log("Redis ping failed", 'fail')
                self.results['cache']['available'] = False
                
        except Exception as e:
            self.results['cache']['available'] = False
            self.results['cache']['error'] = str(e)
            self.log(f"Redis connection failed: {e}", 'fail')
    
    def check_models(self):
        """Check ML model availability."""
        self.log("ML Models", 'info')
        
        models = {
            'face_detector': CV2_AVAILABLE,
            'face_embedder': self._check_insightface(),
            'spoof_detector': CV2_AVAILABLE,
            'emotion_detector': self._check_fer(),
            'age_gender': CV2_AVAILABLE,
            'torch': TORCH_AVAILABLE,
            'faiss': FAISS_AVAILABLE
        }
        
        self.results['models'] = {}
        for name, available in models.items():
            status = 'pass' if available else 'warn'
            self.log(f"{name}: {'available' if available else 'not available (fallback mode)'}", status)
            self.results['models'][name] = available
        
        # Check for model weights
        weights_path = Path('backend/weights')
        if weights_path.exists():
            weight_files = list(weights_path.glob('*'))
            self.results['models']['weights_dir'] = str(weights_path)
            self.results['models']['weight_files'] = [f.name for f in weight_files]
            self.log(f"Model weights directory: {len(weight_files)} files", 'pass')
        else:
            self.log("Model weights directory not found - models may use mock implementations", 'warn')
    
    def _check_insightface(self) -> bool:
        """Check if insightface is available."""
        try:
            import insightface
            return True
        except ImportError:
            return False
    
    def _check_fer(self) -> bool:
        """Check if FER library is available."""
        try:
            from fer import FER
            return True
        except ImportError:
            return False
    
    def check_gpu(self):
        """Check GPU availability and utilization."""
        self.log("GPU Acceleration", 'info')
        
        if not TORCH_AVAILABLE:
            self.log("PyTorch not available - GPU checks skipped", 'warn')
            return
        
        try:
            if torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                self.results['gpu']['available'] = True
                self.results['gpu']['count'] = device_count
                self.log(f"GPU available: {device_count} device(s)", 'pass')
                
                for i in range(device_count):
                    props = torch.cuda.get_device_properties(i)
                    self.log(f"  GPU {i}: {props.name} ({props.total_memory / 1024**3:.1f} GB)", 'info')
                    
                # Check memory usage
                allocated = torch.cuda.memory_allocated(0) / (1024**3)
                reserved = torch.cuda.memory_reserved(0) / (1024**3)
                self.results['gpu']['memory_allocated_gb'] = round(allocated, 2)
                self.results['gpu']['memory_reserved_gb'] = round(reserved, 2)
            else:
                self.results['gpu']['available'] = False
                self.log("No GPU detected - running in CPU mode", 'info')
        except Exception as e:
            self.results['gpu']['error'] = str(e)
            self.log(f"GPU check failed: {e}", 'warn')
    
    def check_network_ports(self):
        """Check if required ports are listening."""
        self.log("Network Ports", 'info')
        
        ports = {
            'PostgreSQL': 5432,
            'Redis': 6379,
            'API (HTTP)': 8000,
            'API (HTTPS)': 443,
            'Frontend': 3000,
            'Prometheus': 9090,
            'gRPC': 50051,
            'Grafana': 3001
               
        }
        
        self.results['network']['ports'] = {}
        
        for service, port in ports.items():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            is_open = result == 0
            self.results['network']['ports'][service] = {
                'port': port,
                'open': is_open
            }
            
            status = 'pass' if is_open else 'fail'
            self.log(f"{service} (:{port}): {'listening' if is_open else 'not responding'}", status)
    
    def check_env_vars(self):
        """Check critical environment variables."""
        self.log("Environment Configuration", 'info')
        
        required_vars = [
            'DATABASE_URL',
            'DB_HOST',
            'DB_PORT',
            'DB_NAME',
            'DB_USER',
            'DB_PASSWORD',
            'JWT_SECRET',
            'ENCRYPTION_KEY',
            'SENTRY_DSN'
        ]
        
        self.results['environment'] = {}
        
        for var in required_vars:
            value = os.getenv(var)
            present = value is not None
            self.results['environment'][var] = present
            
            status = 'pass' if present else 'fail'
            self.log(f"{var}: {'set' if present else 'MISSING'}", status)
    
    def check_docker_services(self):
        """Check Docker container status if applicable."""
        self.log("Docker Services", 'info')
        
        try:
            import subprocess
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}\t{{.Status}}'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                services = {}
                for line in lines:
                    if line:
                        parts = line.split('\t')
                        name = parts[0]
                        status = parts[1] if len(parts) > 1 else 'unknown'
                        services[name] = status
                
                self.results['docker'] = services
                
                # Check expected services
                expected = ['postgres', 'redis', 'backend', 'ui', 'nginx']
                for svc in expected:
                    if svc in services and 'Up' in services[svc]:
                        self.log(f"Container {svc}: running", 'pass')
                    elif svc in services:
                        self.log(f"Container {svc}: {services[svc]}", 'fail')
                    else:
                        self.log(f"Container {svc}: not found", 'warn')
            else:
                self.log("Docker not running or not installed", 'warn')
        except Exception as e:
            self.log(f"Docker check failed: {e}", 'warn')
    
    async def run_all_checks(self):
        """Run all diagnostic checks."""
        self.log("\n" + "="*60, 'info')
        self.log("AI-f SYSTEM DIAGNOSTICS", 'info')
        self.log("="*60 + "\n", 'info')
        
        # System resources
        self.check_system_resources()
        print()
        
        # Environment
        self.check_env_vars()
        print()
        
        # Network ports
        self.check_network_ports()
        print()
        
        # Docker (if applicable)
        if not self.quick:
            self.check_docker_services()
            print()
        
        # Database
        await self.check_database()
        print()
        
        # Redis
        await self.check_redis()
        print()
        
        # Models
        if not self.quick:
            self.check_models()
            print()
        
        # GPU
        if not self.quick:
            self.check_gpu()
            print()
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print diagnostic summary."""
        self.log("\n" + "="*60, 'info')
        self.log("DIAGNOSTIC SUMMARY", 'info')
        self.log("="*60, 'info')
        
        issue_count = len(self.results['issues'])
        warning_count = len(self.results['warnings'])
        passed_count = len(self.results['passed'])
        
        print(f"\n{Color.BOLD}Results:{Color.END}")
        print(f"  {Color.GREEN}Passed: {passed_count}{Color.END}")
        print(f"  {Color.YELLOW}Warnings: {warning_count}{Color.END}")
        print(f"  {Color.RED}Issues: {issue_count}{Color.END}")
        
        if issue_count > 0:
            print(f"\n{Color.RED}{Color.BOLD}Critical Issues:{Color.END}")
            for issue in self.results['issues'][:5]:  # Show top 5
                print(f"  • {issue}")
        
        if warning_count > 0:
            print(f"\n{Color.YELLOW}Warnings:{Color.END}")
            for warning in self.results['warnings'][:5]:
                print(f"  • {warning}")
        
        print()
    
    def to_json(self) -> str:
        """Convert results to JSON."""
        return json.dumps(self.results, indent=2, default=str)
    
    def save_report(self, filepath: str):
        """Save report to file."""
        with open(filepath, 'w') as f:
            if self.output_json:
                json.dump(self.results, f, indent=2, default=str)
            else:
                # Plain text summary
                f.write("AI-f System Diagnostic Report\n")
                f.write(f"Generated: {self.results['timestamp']}\n\n")
                
                f.write("ISSUES:\n")
                for issue in self.results['issues']:
                    f.write(f"  ❌ {issue}\n")
                
                f.write("\nWARNINGS:\n")
                for warning in self.results['warnings']:
                    f.write(f"  ⚠️ {warning}\n")
                
                f.write("\nPASSED CHECKS:\n")
                for passed in self.results['passed']:
                    f.write(f"  ✓ {passed}\n")
        
        self.log(f"Report saved to {filepath}", 'info')


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI-f System Diagnostics')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--output', type=str, help='Save report to file')
    parser.add_argument('--quick', action='store_true', help='Skip heavy checks')
    
    args = parser.parse_args()
    
    diag = SystemDiagnostics(
        output_json=args.json,
        quick=args.quick
    )
    
    try:
        await diag.run_all_checks()
        
        if args.output:
            diag.save_report(args.output)
        elif args.json:
            print(diag.to_json())
        else:
            # Already printed by run_all_checks
            pass
            
    except KeyboardInterrupt:
        print("\nDiagnostics interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"Diagnostics failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
