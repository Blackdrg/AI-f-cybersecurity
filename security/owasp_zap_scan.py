#!/usr/bin/env python3
"""
OWASP ZAP Automated Security Scanner for AI-f
Performs automated security testing of the AI-f API.

Usage:
    python owasp_zap_scan.py --target http://localhost:8000 --apikey zap-api-key
"""

import argparse
import json
import time
import sys
import os
from typing import Dict, List, Optional

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from zapv2 import ZAPv2
except ImportError:
    print("Warning: python-owasp-zap-v2.4 not installed. Install with:")
    print("  pip install python-owasp-zap-v2.4")
    ZAPv2 = None


class ZAPSecurityScanner:
    """OWASP ZAP Security Scanner for AI-f API."""
    
    def __init__(self, target: str, zap_api_key: str, zap_url: str = "http://localhost:8080"):
        """
        Initialize ZAP scanner.
        
        Args:
            target: Target URL to scan (e.g., http://localhost:8000)
            zap_api_key: ZAP API key
            zap_url: ZAP proxy URL (default: http://localhost:8080)
        """
        self.target = target.rstrip('/')
        self.zap_url = zap_url
        self.api_key = zap_api_key
        
        if ZAPv2 is None:
            raise ImportError("ZAPv2 module not available. Install python-owasp-zap-v2.4")
        
        self.zap = ZAPv2(
            apikey=self.api_key,
            proxies={'http': self.zap_url, 'https': self.zap_url}
        )
        
        self.scan_results = {
            'target': self.target,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'alerts': [],
            'summary': {}
        }
    
    def health_check(self) -> bool:
        """Check ZAP health status."""
        try:
            status = self.zap.core.status()
            print(f"[+] ZAP Status: {status}")
            return True
        except Exception as e:
            print(f"[-] ZAP Health Check Failed: {e}")
            return False
    
    def spider_scan(self, max_duration: int = 120) -> str:
        """
        Run spider scan to discover endpoints.
        
        Args:
            max_duration: Maximum spider duration in seconds
            
        Returns:
            Spider scan ID
        """
        print(f"[+] Starting spider scan on {self.target}")
        
        # Start spider
        scan_id = self.zap.spider.scan(self.target, maxchildren=50)
        print(f"[+] Spider scan started: {scan_id}")
        
        # Monitor progress
        progress = 0
        while int(progress) < 100:
            time.sleep(5)
            progress = self.zap.spider.status(scan_id)
            print(f"[+] Spider progress: {progress}%")
            
            # Timeout check
            if int(time.time() - self.start_time) > max_duration:
                print("[!] Spider scan timeout reached")
                break
        
        print(f"[+] Spider scan completed. Results: {self.zap.spider.results(scan_id)}")
        return scan_id
    
    def ajax_spider_scan(self, max_duration: int = 180) -> str:
        """
        Run AJAX spider scan for JavaScript-heavy endpoints.
        
        Args:
            max_duration: Maximum duration in seconds
            
        Returns:
            AJAX spider scan ID
        """
        print(f"[+] Starting AJAX spider scan on {self.target}")
        
        scan_id = self.zap.ajaxSpider.scan(self.target)
        print(f"[+] AJAX spider scan started: {scan_id}")
        
        # Monitor status
        status = self.zap.ajaxSpider.status(scan_id)
        while status == 'running':
            time.sleep(10)
            status = self.zap.ajaxSpider.status(scan_id)
            print(f"[+] AJAX spider status: {status}")
            
            if int(time.time() - self.start_time) > max_duration:
                print("[!] AJAX spider timeout reached")
                break
        
        print(f"[+] AJAX spider scan completed. Status: {status}")
        return scan_id
    
    def active_scan(self, policy: str = 'api-scan', max_duration: int = 600) -> str:
        """
        Run active scan with specified policy.
        
        Args:
            policy: Scan policy name
            max_duration: Maximum scan duration in seconds
            
        Returns:
            Active scan ID
        """
        print(f"[+] Starting active scan with policy: {policy}")
        
        # Get available policies
        policies = self.zap.ascan.scanners()
        policy_map = {p['name']: p['id'] for p in policies}
        
        # Configure aggressive scanning for API
        if policy == 'api-scan':
            # Enable API-specific scanners
            for scanner in policies:
                scanner_id = scanner['id']
                # Enable all scanners for comprehensive scan
                self.zap.ascan.enable_scanners(scanner_id)
        
        # Start active scan
        scan_id = self.zap.ascan.scan(
            self.target,
            recurse=True,
            inscopeonly=True,
            scanpolicyname=policy
        )
        print(f"[+] Active scan started: {scan_id}")
        
        # Monitor progress
        progress = 0
        self.start_time = time.time()
        while int(progress) < 100:
            time.sleep(10)
            progress = self.zap.ascan.status(scan_id)
            elapsed = int(time.time() - self.start_time)
            print(f"[+] Active scan progress: {progress}% (elapsed: {elapsed}s)")
            
            if elapsed > max_duration:
                print("[!] Active scan timeout reached")
                break
        
        print(f"[+] Active scan completed")
        return scan_id
    
    def passive_scan(self) -> List[Dict]:
        """
        Collect passive scan results.
        
        Returns:
            List of passive scan alerts
        """
        print("[+] Collecting passive scan results")
        
        # Passive scanning happens automatically
        # Just collect the results
        alerts = self.zap.core.alerts(baseurl=self.target)
        print(f"[+] Passive scan found {len(alerts)} alerts")
        
        return alerts
    
    def get_alerts(self, risk_level: Optional[str] = None) -> List[Dict]:
        """
        Get scan alerts with optional risk filtering.
        
        Args:
            risk_level: Filter by risk (None, 'Informational', 'Low', 'Medium', 'High')
            
        Returns:
            List of alerts
        """
        alerts = self.zap.core.alerts(baseurl=self.target)
        
        if risk_level:
            alerts = [a for a in alerts if a.get('risk') == risk_level]
        
        return alerts
    
    def generate_report(self) -> Dict:
        """
        Generate comprehensive security scan report.
        
        Returns:
            Scan report dictionary
        """
        print("[+] Generating security scan report")
        
        alerts = self.zap.core.alerts(baseurl=self.target)
        
        # Categorize by risk
        risk_counts = {
            'High': 0,
            'Medium': 0,
            'Low': 0,
            'Informational': 0
        }
        
        alert_details = []
        for alert in alerts:
            risk = alert.get('risk', 'Informational')
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
            
            alert_details.append({
                'name': alert.get('name', 'Unknown'),
                'risk': risk,
                'confidence': alert.get('confidence', 'Unknown'),
                'description': alert.get('description', '')[:200],
                'url': alert.get('url', ''),
                'solution': alert.get('solution', '')[:200]
            })
        
        self.scan_results['alerts'] = alert_details
        self.scan_results['summary'] = {
            'total_alerts': len(alerts),
            'risk_distribution': risk_counts,
            'endpoints_scanned': len(set(a.get('url', '') for a in alerts))
        }
        
        return self.scan_results
    
    def save_report(self, output_format: str = 'json', filename: Optional[str] = None) -> str:
        """
        Save scan report to file.
        
        Args:
            output_format: Report format (json, html, xml)
            filename: Output filename (auto-generated if None)
            
        Returns:
            Path to saved report
        """
        if filename is None:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f"zap_report_{timestamp}.{output_format}"
        
        filepath = os.path.join(os.getcwd(), filename)
        
        if output_format == 'json':
            with open(filepath, 'w') as f:
                json.dump(self.scan_results, f, indent=2)
        elif output_format == 'html':
            html_report = self.zap.core.htmlreport()
            with open(filepath, 'w') as f:
                f.write(html_report)
        elif output_format == 'xml':
            xml_report = self.zap.core.xmlreport()
            with open(filepath, 'w') as f:
                f.write(xml_report)
        else:
            raise ValueError(f"Unsupported format: {output_format}")
        
        print(f"[+] Report saved to: {filepath}")
        return filepath
    
    def run_full_scan(self, max_duration: int = 1800) -> Dict:
        """
        Run full security scan (spider + AJAX + active + passive).
        
        Args:
            max_duration: Maximum total scan duration
            
        Returns:
            Scan results
        """
        print(f"="*60)
        print(f"AI-f Security Scan")
        print(f"Target: {self.target}")
        print(f"ZAP: {self.zap_url}")
        print(f"="*60)
        
        self.start_time = time.time()
        
        # Health check
        if not self.health_check():
            raise RuntimeError("ZAP is not running or not accessible")
        
        # Spider scan
        try:
            self.spider_scan(max_duration=300)
        except Exception as e:
            print(f"[!] Spider scan failed: {e}")
        
        # AJAX spider
        try:
            self.ajax_spider_scan(max_duration=300)
        except Exception as e:
            print(f"[!] AJAX spider failed: {e}")
        
        # Active scan (focused on API)
        try:
            # Add API endpoints to context
            api_endpoints = [
                f"{self.target}/api/health",
                f"{self.target}/api/recognize",
                f"{self.target}/api/enroll",
                f"{self.target}/api/persons",
                f"{self.target}/api/metrics",
                f"{self.target}/api-docs",
                f"{self.target}/docs"
            ]
            
            for endpoint in api_endpoints:
                try:
                    self.zap.core.access_url(endpoint)
                except:
                    pass
            
            self.active_scan(policy='api-scan', max_duration=600)
        except Exception as e:
            print(f"[!] Active scan failed: {e}")
        
        # Collect passive results
        try:
            self.passive_scan()
        except Exception as e:
            print(f"[!] Passive scan failed: {e}")
        
        # Generate report
        results = self.generate_report()
        
        elapsed = int(time.time() - self.start_time)
        print(f"\n{'='*60}")
        print(f"Scan Complete")
        print(f"Duration: {elapsed}s")
        print(f"Total Alerts: {results['summary']['total_alerts']}")
        print(f"Risk Distribution: {results['summary']['risk_distribution']}")
        print(f"{'='*60}")
        
        return results


def main():
    parser = argparse.ArgumentParser(description='OWASP ZAP Security Scanner for AI-f')
    parser.add_argument('--target', required=True, help='Target URL (e.g., http://localhost:8000)')
    parser.add_argument('--apikey', required=True, help='ZAP API key')
    parser.add_argument('--zap-url', default='http://localhost:8080', help='ZAP proxy URL')
    parser.add_argument('--format', default='json', choices=['json', 'html', 'xml'], help='Report format')
    parser.add_argument('--output', help='Output filename')
    parser.add_argument('--max-duration', type=int, default=1800, help='Max scan duration (seconds)')
    
    args = parser.parse_args()
    
    try:
        scanner = ZAPSecurityScanner(
            target=args.target,
            zap_api_key=args.apikey,
            zap_url=args.zap_url
        )
        
        results = scanner.run_full_scan(max_duration=args.max_duration)
        scanner.save_report(output_format=args.format, filename=args.output)
        
        # Exit with error code if high-risk issues found
        high_risk = results['summary']['risk_distribution'].get('High', 0)
        if high_risk > 0:
            print(f"\n[!] WARNING: {high_risk} high-risk issues found!")
            sys.exit(1)
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\n[!] Scan failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == '__main__':
    main()
