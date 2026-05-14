"""
Comprehensive test suite for all threat intelligence and SOAR features.
"""
import pytest
import asyncio
import json
import sys
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

# Mock asyncpg before imports
mock_asyncpg = MagicMock()
sys.modules['asyncpg'] = mock_asyncpg


class TestIOCModel:
    """Test IOC data model."""

    def test_ioc_creation_defaults(self):
        from app.services.ioc_repository import IOC, IOCStatus
        ioc = IOC(indicator="192.168.1.1", ioc_type="ip", source="test")
        assert ioc.ioc_id is not None
        assert len(ioc.ioc_id) == 36
        assert ioc.status == IOCStatus.NEW
        assert ioc.is_active is True
        assert ioc.seen_count == 1
        assert ioc.fingerprint() is not None

    def test_ioc_fingerprint_unique(self):
        from app.services.ioc_repository import IOC
        ioc1 = IOC(indicator="192.168.1.1", ioc_type="ip", source="otx")
        ioc3 = IOC(indicator="10.0.0.1", ioc_type="ip", source="otx")
        assert ioc1.fingerprint() != ioc3.fingerprint()

    def test_ioc_to_dict(self):
        from app.services.ioc_repository import IOC
        ioc = IOC(indicator="evil.com", ioc_type="domain", source="otx")
        d = ioc.to_dict()
        assert d["indicator"] == "evil.com"
        assert d["ioc_type"] == "domain"
        assert "created_at" in d


class TestThreatIntelProvider:
    """Test Threat Intel Provider functionality."""

    def test_provider_creation(self):
        with patch.dict('os.environ', {}, clear=True):
            from app.providers.threat_intel_provider import ThreatIntelProvider
            provider = ThreatIntelProvider()
            assert provider is not None

    def test_ioc_type_detection(self):
        with patch.dict('os.environ', {}, clear=True):
            from app.providers.threat_intel_provider import ThreatIntelProvider
            provider = ThreatIntelProvider()
            assert provider._detect_ioc_type("192.168.1.1") == "ip"
            assert provider._detect_ioc_type("example.com") == "domain"
            assert provider._detect_ioc_type("https://example.com/path") == "url"
            assert provider._detect_ioc_type("d41d8cd98f00b204e9800998ecf8427e") == "md5"

    def test_cache_operations(self):
        with patch.dict('os.environ', {}, clear=True):
            from app.providers.threat_intel_provider import ThreatIntelProvider
            from datetime import timedelta
            provider = ThreatIntelProvider()
            provider._set_cache("test:key", {"data": "value"})
            result = provider._get_cache("test:key")
            assert result == {"data": "value"}
            assert provider._is_cached("test:key") is True
            provider._cache_timestamps["test:key"] = datetime.utcnow() - timedelta(hours=2)
            assert provider._is_cached("test:key") is False


class TestVirusTotalProvider:
    """Test VirusTotal provider."""

    def test_creation_unconfigured(self):
        with patch.dict('os.environ', {}, clear=True):
            from app.providers.virustotal_provider import VirusTotalProvider
            vt = VirusTotalProvider()
            assert vt.is_configured() is False

    def test_parse_file_response(self):
        with patch.dict('os.environ', {'VIRUS_TOTAL_API_KEY': 'test_key'}):
            from app.providers.virustotal_provider import VirusTotalProvider
            vt = VirusTotalProvider()
            data = {
                "attributes": {
                    "type_description": "PE32 executable",
                    "meaningful_name": "malware.exe",
                    "md5": "d41d8cd98f00b204e9800998ecf8427e",
                    "size": 1024,
                    "last_analysis_stats": {"malicious": 50, "suspicious": 10, "harmless": 30, "undetected": 10},
                }
            }
            result = vt._parse_file_response(data)
            assert result["found"] is True
            assert result["threat_score"] == 50

    def test_parse_domain_response(self):
        with patch.dict('os.environ', {'VIRUS_TOTAL_API_KEY': 'test_key'}):
            from app.providers.virustotal_provider import VirusTotalProvider
            vt = VirusTotalProvider()
            data = {
                "id": "example.com",
                "attributes": {
                    "last_analysis_stats": {"malicious": 5, "suspicious": 3, "harmless": 20, "undetected": 2},
                    "categories": {"Adult": "Content"},
                    "reputation": 50,
                    "tags": ["phishing"]
                }
            }
            result = vt._parse_domain_response(data)
            assert result["found"] is True
            assert result["domain"] == "example.com"


class TestURLhausProvider:
    """Test URLhaus provider."""

    def test_creation(self):
        from app.providers.urlhaus_provider import URLhausProvider
        provider = URLhausProvider()
        assert provider.is_configured() is False


class TestEmergingThreatsProvider:
    """Test Emerging Threats provider."""

    def test_severity_mapping(self):
        from app.providers.emerging_threats_provider import EmergingThreatsProvider
        assert EmergingThreatsProvider._severity_to_score("low") == 20
        assert EmergingThreatsProvider._severity_to_score("critical") == 100


class TestSTIXTaxiiProvider:
    """Test STIX/TAXII provider."""

    def test_pattern_extraction(self):
        from app.providers.stix_taxii_provider import STIXTaxiiClient
        assert STIXTaxiiClient._extract_pattern_value("file:hashes.MD5 = 'abc123'") == "abc123"
        assert STIXTaxiiClient._extract_pattern_value("domain:value = 'evil.com'") == "evil.com"

    def test_ioc_type_inference(self):
        from app.providers.stix_taxii_provider import STIXTaxiiClient
        assert STIXTaxiiClient._infer_ioc_type("[ipv4-addr:value = '1.2.3.4']") == "ip"
        assert STIXTaxiiClient._infer_ioc_type("[domain:value = 'evil.com']") == "domain"


class TestThreatIntelCache:
    """Test cache layer."""

    def test_creation(self):
        from app.services.threat_cache import ThreatIntelCache
        cache = ThreatIntelCache()
        assert cache is not None


class TestConnectorEngine:
    """Test connector engine."""

    def test_connector_creation(self):
        from app.services.connector_engine import BaseConnector, ConnectorType, ConnectorStatus
        conn = BaseConnector("test", ConnectorType.SIEM, {})
        assert conn.name == "test"
        assert conn.connector_type == ConnectorType.SIEM
        assert conn.status == ConnectorStatus.UNCONFIGURED

    def test_registry(self):
        from app.services.connector_engine import ConnectorRegistry, BaseConnector, ConnectorType
        registry = ConnectorRegistry()
        conn = BaseConnector("test", ConnectorType.SIEM, {})
        registry.register(conn)
        assert registry.get("test") is conn
        registry.deregister("test")
        assert registry.get("test") is None

    def test_registry_by_type(self):
        from app.services.connector_engine import ConnectorRegistry, BaseConnector, ConnectorType
        registry = ConnectorRegistry()
        conn1 = BaseConnector("siem1", ConnectorType.SIEM, {})
        conn2 = BaseConnector("notify1", ConnectorType.NOTIFICATION, {})
        registry.register(conn1)
        registry.register(conn2)
        siems = registry.get_by_type(ConnectorType.SIEM)
        assert len(siems) == 1


class TestWorkflowTriggers:
    """Test workflow trigger matching."""

    def test_event_match(self):
        from app.services.orchestrated_response import WorkflowTrigger
        trigger = WorkflowTrigger("test", "event", {"event_type": "threat"}, "workflow1")
        matched, confidence = trigger.matches({"event_type": "threat"})
        assert matched is True

    def test_event_no_match(self):
        from app.services.orchestrated_response import WorkflowTrigger
        trigger = WorkflowTrigger("test", "event", {"event_type": "threat"}, "workflow1")
        matched, confidence = trigger.matches({"event_type": "other"})
        assert matched is False

    def test_numeric_comparison(self):
        from app.services.orchestrated_response import WorkflowTrigger
        trigger = WorkflowTrigger("test", "event", {"count": {"min": 5}}, "workflow1")
        matched, _ = trigger.matches({"count": 10})
        assert matched is True
        matched, _ = trigger.matches({"count": 3})
        assert matched is False


class TestComplianceEngine:
    """Test compliance engine."""

    def test_engine_creation(self):
        from app.services.compliance_engine import ComplianceEngine
        engine = ComplianceEngine()
        assert engine is not None
        assert len(engine.controls) > 0

    def test_get_controls_by_framework(self):
        from app.services.compliance_engine import ComplianceEngine
        engine = ComplianceEngine()
        soc2 = engine.get_controls_by_framework("SOC2")
        assert len(soc2) > 0

    def test_compliance_summary(self):
        from app.services.compliance_engine import ComplianceEngine
        engine = ComplianceEngine()
        summary = engine.get_compliance_summary()
        assert "SOC2" in summary

    def test_gap_identification(self):
        from app.services.compliance_engine import ComplianceEngine
        engine = ComplianceEngine()
        gaps = engine.get_gaps()
        assert isinstance(gaps, list)


class TestSDKValidator:
    """Test SDK validation."""

    def test_validator_creation(self):
        from app.sdk_validation import SDKValidator
        validator = SDKValidator()
        assert validator is not None


class TestThreatEnrichmentPipeline:
    """Test threat enrichment pipeline."""

    def test_pipeline_creation(self):
        from app.services.threat_enrichment_pipeline import ThreatEnrichmentPipeline
        pipeline = ThreatEnrichmentPipeline()
        assert pipeline is not None

    def test_type_detection(self):
        from app.services.threat_enrichment_pipeline import ThreatEnrichmentPipeline
        pipeline = ThreatEnrichmentPipeline()
        assert pipeline._detect_type("1.2.3.4") == "ip"
        assert pipeline._detect_type("evil.com") == "domain"
        assert pipeline._detect_type("http://evil.com") == "url"

    def test_risk_classification(self):
        from app.services.threat_enhanced_recognition import _classify_risk
        assert _classify_risk(90) == "critical"
        assert _classify_risk(65) == "high"
        assert _classify_risk(45) == "medium"
        assert _classify_risk(25) == "low"


class TestFeedSyncTasks:
    """Test feed sync tasks exist."""

    def test_import_tasks_module(self):
        from app.tasks.threat_intel_tasks import (
            refresh_urlhaus_feed, refresh_otx_pulses,
            refresh_emerging_threats, refresh_stix_taxii_feeds,
            expire_old_iocs, deduplicate_iocs
        )
        assert callable(refresh_urlhaus_feed)
        assert callable(refresh_otx_pulses)
        assert callable(refresh_emerging_threats)
        assert callable(refresh_stix_taxii_feeds)
        assert callable(expire_old_iocs)
        assert callable(deduplicate_iocs)

    def test_orchestrator_class(self):
        from app.tasks.threat_intel_tasks import IOCRefreshOrchestrator
        assert hasattr(IOCRefreshOrchestrator, "refresh_all_feeds")
        assert hasattr(IOCRefreshOrchestrator, "run_cleanup")


class TestObservability:
    """Test observability module."""

    def test_json_formatter(self):
        import logging
        import json
        from app.monitoring.observability import JSONFormatter
        formatter = JSONFormatter(service_name="test")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="Test message", args=None, exc_info=None
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["service"] == "test"

    def test_error_aggregator(self):
        from app.monitoring.observability import ErrorAggregator
        agg = ErrorAggregator()
        result = agg.record_error("test", "module")
        assert result["fingerprint"] == "test:module"

    def test_alerting_service(self):
        from app.monitoring.observability import AlertRule
        rule = AlertRule("test", {"op": ">", "threshold": 100}, "critical", [])
        assert rule.check(150) is True
        assert rule.check(50) is False


class TestPerformanceValidator:
    """Test performance validation suite."""

    def test_result_creation(self):
        from app.tests.test_performance_validated import PerfResult
        result = PerfResult(
            test_name="test", passed=True, metric="latency",
            achieved=100.0, target=300.0, unit="ms"
        )
        assert result.passed is True

    def test_validator_summary(self):
        from app.tests.test_performance_validated import PerformanceValidator
        validator = PerformanceValidator(test_mode=True)
        validator._results.append(validator.test_p99_latency())
        summary = validator.summary()
        assert summary["total_tests"] >= 1