#!/usr/bin/env python3
"""
AI-f Log Analyzer

Analyzes system logs, identifies patterns, and generates reports:
- Error frequency analysis
- Performance trend detection
- Security anomaly detection
- Resource utilization patterns
"""

import sys
import os
import re
import json
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Common log patterns
ERROR_PATTERN = re.compile(r'ERROR|CRITICAL|FATAL', re.IGNORECASE)
WARNING_PATTERN = re.compile(r'WARNING|WARN', re.IGNORECASE)
TIMESTAMP_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}|\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}')
LOG_LEVEL_PATTERN = re.compile(r'\[(DEBUG|INFO|WARNING|ERROR|CRITICAL)\]')

class LogAnalyzer:
    """Analyzes AI-f log files."""
    
    def __init__(self, log_dir: str = 'logs'):
        self.log_dir = Path(log_dir)
        self.results = {
            'files_analyzed': [],
            'total_lines': 0,
            'errors': [],
            'warnings': [],
            'errors_by_type': Counter(),
            'errors_by_file': Counter(),
            'performance_metrics': [],
            'security_events': [],
            ' anomalous_patterns': []
        }
    
    def find_log_files(self) -> List[Path]:
        """Find all log files."""
        log_files = []
        
        if not self.log_dir.exists():
            # Try common locations
            locations = [
                Path('/var/log/ai-f'),
                Path('./logs'),
                Path('/tmp'),
                Path('.')
            ]
            for loc in locations:
                files = list(loc.glob('*.log')) + list(loc.glob('ai-f-*.log'))
                if files:
                    log_files.extend(files)
                    break
        else:
            log_files = list(self.log_dir.glob('*.log')) + list(self.log_dir.glob('*.log.*'))
        
        return log_files
    
    def parse_log_line(self, line: str) -> Optional[Dict]:
        """Parse a log line into structured data."""
        # Try JSON format first
        try:
            data = json.loads(line)
            return {
                'type': 'json',
                'timestamp': data.get('timestamp', data.get('time', '')),
                'level': data.get('level', 'INFO'),
                'message': data.get('message', ''),
                'source': data.get('name', data.get('logger', '')),
                'data': data
            }
        except json.JSONDecodeError:
            pass
        
        # Try standard Python logging format
        match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\w+) - (\w+) - (.*)', line)
        if match:
            return {
                'type': 'python',
                'timestamp': match.group(1),
                'level': match.group(3),
                'source': match.group(2),
                'message': match.group(4)
            }
        
        # Try Nginx log format
        nginx_match = re.match(
            r'.* - - \[(.*?)\] ".*?" \d+ \d+ ".*?" ".*?"',
            line
        )
        if nginx_match:
            return {
                'type': 'nginx',
                'timestamp': nginx_match.group(1),
                'level': 'INFO',
                'source': 'nginx',
                'message': line
            }
        
        return None
    
    def analyze_file(self, filepath: Path) -> Dict:
        """Analyze a single log file."""
        stats = {
            'file': str(filepath),
            'lines': 0,
            'errors': 0,
            'warnings': 0,
            'infos': 0,
            'error_types': Counter(),
            'error_times': [],
            'performance_metrics': []
        }
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    stats['lines'] += 1
                    
                    parsed = self.parse_log_line(line.strip())
                    if not parsed:
                        continue
                    
                    level = parsed['level'].upper()
                    message = parsed['message']
                    
                    # Count by level
                    if level == 'ERROR':
                        stats['errors'] += 1
                        stats['error_types'][message[:100]] += 1
                        stats['error_times'].append(parsed['timestamp'])
                        self.results['errors'].append({
                            'file': str(filepath),
                            'line': line_num,
                            'message': message[:200]
                        })
                    elif level == 'WARNING' or level == 'WARN':
                        stats['warnings'] += 1
                        self.results['warnings'].append({
                            'file': str(filepath),
                            'line': line_num,
                            'message': message[:200]
                        })
                    elif level == 'INFO':
                        stats['infos'] += 1
                    
                    # Look for performance metrics
                    if 'latency' in message.lower() or 'processing_time' in message.lower():
                        stats['performance_metrics'].append(message[:200])
                    
                    # Look for security events
                    security_keywords = ['spoof', 'anomaly', 'unauthorized', 'forbidden', 'attack']
                    if any(keyword in message.lower() for keyword in security_keywords):
                        self.results['security_events'].append({
                            'file': str(filepath),
                            'line': line_num,
                            'message': message[:200]
                        })
        
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
        
        return stats
    
    def analyze_all(self):
        """Analyze all log files."""
        print("="*60)
        print("AI-f LOG ANALYSIS")
        print("="*60 + "\n")
        
        log_files = self.find_log_files()
        
        if not log_files:
            print("⚠️  No log files found.")
            return self.results
        
        print(f"Found {len(log_files)} log file(s):\n")
        
        for log_file in log_files:
            print(f"Analyzing: {log_file.name}...")
            stats = self.analyze_file(log_file)
            self.results['total_lines'] += stats['lines']
            self.results['files_analyzed'].append(stats)
            
            print(f"  Lines: {stats['lines']}")
            print(f"  Errors: {stats['errors']}")
            print(f"  Warnings: {stats['warnings']}")
            
            if stats['error_types']:
                print("  Top error types:")
                for err, count in stats['error_types'].most_common(3):
                    print(f"    - {err[:70]}... ({count}x)")
            print()
        
        # Cross-file analysis
        self.analyze_patterns()
        
        return self.results
    
    def analyze_patterns(self):
        """Identify patterns across all files."""
        # Error burst detection
        error_times = []
        for file_stats in self.results['files_analyzed']:
            error_times.extend(file_stats.get('error_times', []))
        
        if len(error_times) > 10:
            # Sort times and look for bursts
            sorted_times = sorted(error_times)
            burst_threshold = 60  # 60 seconds
            burst_count = 0
            current_burst = 1
            
            for i in range(1, len(sorted_times)):
                try:
                    t1 = datetime.strptime(sorted_times[i-1], '%Y-%m-%d %H:%M:%S,%f')
                    t2 = datetime.strptime(sorted_times[i], '%Y-%m-%d %H:%M:%S,%f')
                    delta = (t2 - t1).total_seconds()
                    
                    if delta <= burst_threshold:
                        current_burst += 1
                    else:
                        if current_burst > 5:
                            burst_count += 1
                        current_burst = 1
                except:
                    continue
            
            if current_burst > 5:
                burst_count += 1
            
            if burst_count > 0:
                self.results['anomalous_patterns'].append(
                    f"Error bursts detected: {burst_count} instances with >5 errors in 60s"
                )
    
    def generate_report(self, format: str = 'text') -> str:
        """Generate analysis report."""
        if format == 'json':
            return json.dumps(self.results, indent=2, default=str)
        
        # Text format
        lines = []
        lines.append("="*60)
        lines.append("AI-f LOG ANALYSIS REPORT")
        lines.append("="*60)
        lines.append(f"Generated: {datetime.now().isoformat()}")
        lines.append(f"Files analyzed: {len(self.results['files_analyzed'])}")
        lines.append(f"Total lines: {self.results['total_lines']}")
        lines.append("")
        
        # Summary
        total_errors = sum(f['errors'] for f in self.results['files_analyzed'])
        total_warnings = sum(f['warnings'] for f in self.results['files_analyzed'])
        
        lines.append("SUMMARY:")
        lines.append(f"  Errors: {total_errors}")
        lines.append(f"  Warnings: {total_warnings}")
        lines.append(f"  Security events: {len(self.results['security_events'])}")
        lines.append("")
        
        # Top error types
        all_errors = []
        for file_stats in self.results['files_analyzed']:
            if 'error_types' in file_stats:
                for err, count in file_stats['error_types'].items():
                    all_errors.append((err, count))
        
        error_counter = Counter()
        for err, count in all_errors:
            error_counter[err] += count
        
        if error_counter:
            lines.append("TOP ERROR TYPES:")
            for err, count in error_counter.most_common(10):
                lines.append(f"  [{count}x] {err[:70]}")
            lines.append("")
        
        # Security events
        if self.results['security_events']:
            lines.append("SECURITY EVENTS:")
            for event in self.results['security_events'][:10]:
                lines.append(f"  ⚠️  {event['message'][:80]}")
            lines.append("")
        
        # Anomalous patterns
        if self.results['anomalous_patterns']:
            lines.append("ANOMALOUS PATTERNS:")
            for pattern in self.results['anomalous_patterns']:
                lines.append(f"  ⚠️  {pattern}")
            lines.append("")
        
        # Recommendations
        lines.append("RECOMMENDATIONS:")
        if total_errors > 100:
            lines.append("  • High error count - review service logs for root cause")
        if len(self.results['security_events']) > 0:
            lines.append("  • Security events detected - investigate immediately")
        if any('anon' in str(e).lower() for e in self.results['issues']):
            lines.append("  • Some checks failed - run diagnostics.py for details")
        
        return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='AI-f Log Analyzer')
    parser.add_argument('--log-dir', type=str, default='logs', 
                       help='Directory containing log files')
    parser.add_argument('--json', action='store_true', 
                       help='Output JSON format')
    parser.add_argument('--output', type=str, 
                       help='Save report to file')
    parser.add_argument('--since', type=str,
                       help='Only analyze logs since date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    analyzer = LogAnalyzer(args.log_dir)
    analyzer.analyze_all()
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(analyzer.generate_report(args.json))
        print(f"Report saved to {args.output}")
    elif args.json:
        print(analyzer.generate_report(True))
    else:
        print(analyzer.generate_report())


if __name__ == '__main__':
    main()
