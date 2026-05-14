from enum import Enum
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
from uuid import UUID


class StandardResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


class EnrollRequest(BaseModel):
    name: Optional[str] = None
    metadata: Dict[str, Any] = {}
    consent: bool
    camera_id: Optional[str] = None
    voice_files: Optional[List[str]] = None
    gait_video: Optional[str] = None
    physiological_data: Optional[Dict[str, Any]] = None


class EnrollResponse(BaseModel):
    person_id: str
    num_embeddings: int
    example_embedding_id: str
    confidence: Optional[float] = None
    message: str


class RecognizeRequest(BaseModel):
    top_k: int = 1
    threshold: float = 0.4
    camera_id: Optional[str] = None
    enable_spoof_check: bool = True
    enable_emotion: bool = True
    enable_age_gender: bool = True
    enable_behavior: bool = True
    voice_file: Optional[str] = None
    gait_video: Optional[str] = None
    physiological_data: Optional[Dict[str, Any]] = None


class FaceMatch(BaseModel):
    person_id: str
    name: Optional[str]
    score: float
    distance: float


class DetectedFace(BaseModel):
    face_box: List[int]
    face_embedding_id: Optional[str]
    matches: List[FaceMatch]
    inference_ms: float
    is_unknown: bool = False
    spoof_score: Optional[float] = None
    reconstruction_confidence: Optional[float] = None
    emotion: Optional[Dict[str, Any]] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    behavior: Optional[Dict[str, Any]] = None
    identity_score: float
    decision: str
    risk_level: str
    decision_factors: List[Dict[str, Any]]
    hallucination_risk: Optional[Dict[str, Any]] = None
    confidence_interval: Optional[Tuple[float, float]] = None


class RecognizeResponse(BaseModel):
    faces: List[DetectedFace]


class PersonResponse(BaseModel):
    person_id: str
    name: Optional[str]
    embeddings: List[str]
    consent_record: Dict[str, Any]


class RevokeRequest(BaseModel):
    reason: Optional[str] = None


class ConsentVaultRequest(BaseModel):
    action: str
    biometric_type: Optional[str] = None


class ZKPRequest(BaseModel):
    proof: Dict[str, Any]
    challenge: str


class BiasReport(BaseModel):
    demographic_parity_difference: float
    equalized_odds_difference: float


class DeleteResponse(BaseModel):
    deleted: bool
    message: str


# SaaS Schemas
class UserCreate(BaseModel):
    email: str
    name: str
    password: Optional[str] = None
    subscription_tier: Optional[str] = "free"


class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    subscription_tier: str
    created_at: str


class PlanResponse(BaseModel):
    plan_id: str
    name: str
    price: float
    features: List[str]
    limits: Dict[str, Any]


class PlanCreate(BaseModel):
    plan_id: str
    name: str
    price: float
    features: List[str]
    limits: Dict[str, Any]


class SubscriptionCreate(BaseModel):
    plan_id: str


class SubscriptionResponse(BaseModel):
    subscription_id: str
    user_id: str
    plan_id: str
    status: str
    created_at: str
    expires_at: Optional[str]


class PaymentCreate(BaseModel):
    plan_id: str
    amount: float


class PaymentResponse(BaseModel):
    payment_id: str
    user_id: str
    amount: float
    currency: str
    status: str
    stripe_payment_id: Optional[str]
    created_at: str


class OrganizationCreate(BaseModel):
    name: str
    billing_email: str


class OrganizationResponse(BaseModel):
    org_id: str
    name: str
    billing_email: str
    subscription_tier: str
    created_at: Optional[Any]


class OrgMemberAdd(BaseModel):
    user_id: str
    role: str


class CameraCreate(BaseModel):
    name: str
    rtsp_url: Optional[str] = None
    location: Optional[str] = None


class CameraResponse(BaseModel):
    camera_id: str
    org_id: str
    name: str
    rtsp_url: Optional[str]
    location: Optional[str]
    status: str
    created_at: Any


class RecognitionEventResponse(BaseModel):
    event_id: str
    org_id: str
    camera_id: Optional[str]
    person_id: Optional[str]
    person_name: Optional[str]
    camera_name: Optional[str]
    confidence_score: float
    timestamp: Any


class AIAssistantRequest(BaseModel):
    query: str


class AIAssistantResponse(BaseModel):
    model_config = {'protected_namespaces': ()}
    query: str
    response: str
    model_used: str


class MetricsResponse(BaseModel):
    num_persons: int
    num_embeddings: int
    num_audit_logs: int
    num_feedback: int
    db_size: Optional[str] = None
    recognition_count: int
    enroll_count: int
    avg_latency_ms: float
    false_accepts: int
    false_rejects: int
    index_size: int


class LogEntry(BaseModel):
    timestamp: str
    action: str
    person_id: Optional[str]
    details: Dict[str, Any]


class LogsResponse(BaseModel):
    logs: List[LogEntry]


class FederatedUpdate(BaseModel):
    model_config = {'protected_namespaces': ()}
    device_id: str
    model_gradients: Dict[str, Any]
    num_samples: int
    timestamp: str


class ModelVersion(BaseModel):
    model_config = {'protected_namespaces': ()}
    version_id: str
    model_data: bytes
    created_at: str
    description: Optional[str] = None


class EdgeDeviceRequest(BaseModel):
    model_config = {'protected_namespaces': ()}
    device_id: str
    action: str
    model_version: Optional[str] = None


class MultiCameraRequest(BaseModel):
    camera_ids: List[str]
    sync_timestamps: List[str]
    streams: List[str]


class OTADownload(BaseModel):
    model_config = {'protected_namespaces': ()}
    device_id: str
    model_version: str


class AnalyticsResponse(BaseModel):
    time_series: List[Dict[str, Any]]
    bias_trends: List[Dict[str, Any]]
    device_stats: List[Dict[str, Any]]


class QueryPerformanceRequest(BaseModel):
    queries: List[Dict[str, Any]]


class QueryPerformanceEntry(BaseModel):
    name: str
    query: str
    execution_time_ms: float
    rows_returned: int
    timestamp: str


class QueryPerformanceResponse(BaseModel):
    results: List[QueryPerformanceEntry]
    summary: Dict[str, Any]


class UsageResponse(BaseModel):
    user_id: str
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    recognitions_used: int
    enrollments_used: int
    recognitions_limit: int
    enrollments_limit: int


class SupportTicketCreate(BaseModel):
    subject: str
    description: str
    priority: str = "medium"


class SupportTicketUpdate(BaseModel):
    subject: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None


class SupportTicketResponse(BaseModel):
    ticket_id: str
    user_id: str
    subject: str
    description: str
    priority: str
    status: str
    created_at: str
    updated_at: Optional[str] = None


class ConsentRequest(BaseModel):
    subject_id: Optional[str] = None
    purpose: str
    consent_text_version: str = "v1"


class ConsentResponse(BaseModel):
    consent_id: str
    token: str
    expires_at: str
    message: str


class PublicEnrichRequest(BaseModel):
    person_id: Optional[str] = None
    identifiers: Dict[str, str]
    requested_by: str
    purpose: str
    consent_token: Optional[str] = None
    providers: List[str] = ["bing", "wikipedia"]


class ProviderResult(BaseModel):
    provider: str
    title: str
    snippet: str
    url: str
    confidence: float
    raw: Optional[Dict[str, Any]] = None


class PublicEnrichResponse(BaseModel):
    enrich_id: str
    results: List[ProviderResult]
    created_at: str
    expires_at: str
    flags: Dict[str, Any] = {}


class EnrichResultDetail(BaseModel):
    enrich_id: str
    query: str
    subject: str
    summary: List[ProviderResult]
    created_at: str
    expires_at: str
    requested_by: str
    purpose: str


class AuditLogEntry(BaseModel):
    audit_id: str
    action: str
    user_id: str
    target_enrich_id: Optional[str] = None
    provider_calls: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: str


class HashChainedAuditLog(BaseModel):
    id: Optional[int] = None
    action: str
    person_id: Optional[UUID] = None
    details: Dict[str, Any]
    previous_hash: Optional[str] = None
    hash: str
    zkp_proof: Optional[Dict[str, Any]] = None
    timestamp: Any


class AuditLogsResponse(BaseModel):
    logs: List[AuditLogEntry]
    total: int


class FlagForReviewRequest(BaseModel):
    reason: Optional[str] = None


# ===== Threat Intelligence & SOAR Schemas =====

class IOCType(str, Enum):
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    DOMAIN = "domain"
    URL = "url"
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    EMAIL = "email"


class IOCSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IOCSource(str, Enum):
    OTX = "otx"
    MISP = "misp"
    VIRUSTOTAL = "virustotal"
    ABUSEIPDB = "abuseipdb"
    URLHAUS = "urlhaus"
    EMERGING_THREATS = "emerging_threats"
    STIX_TAXII = "stix_taxii"
    INTERNAL = "internal"


class IOCEnrichmentRequest(BaseModel):
    """Request for IOC enrichment."""
    indicator: str
    ioc_type: Optional[str] = "auto"
    force_refresh: bool = False


class IOCEnrichmentResult(BaseModel):
    """Enriched IOC result from multiple sources."""
    indicator: str
    ioc_type: str
    threat_score: int
    malicious: bool
    confidence: float
    sources: List[str]
    tags: List[str]
    last_seen: Optional[str]
    first_seen: Optional[str]
    seen_count: int = 1
    details: Dict[str, Any] = {}
    cached: bool = False
    enriched_at: str


class ThreatFeedResponse(BaseModel):
    """Response for threat feed endpoint."""
    feed: List[Dict[str, Any]]
    provider_status: str
    last_updated: str
    total_returned: int


class EnrichIndicatorRequest(BaseModel):
    """Request to enrich a single indicator."""
    indicator: str
    type: str = "auto"


class CorrelationEvent(BaseModel):
    """Event correlation data."""
    correlation_id: str
    org_id: str
    event_type: str
    indicator_type: str
    indicators: List[str]
    threat_score: int
    risk_level: str
    timestamp: str


class EnrichmentSummary(BaseModel):
    """Summary of enrichment for a recognition event."""
    sources_checked: int
    highest_threat_score: int
    ioc_matches: int
    risk_level: str
    cached: bool
    enrichment_time_ms: float


class WorkflowAction(BaseModel):
    """A single workflow action to execute."""
    action_type: str
    parameters: Dict[str, Any] = {}
    timeout_seconds: int = 300
    requires_approval: bool = False
    rollback_action: str = ""


class IncidentWorkflow(BaseModel):
    """Incident workflow definition."""
    name: str
    description: str
    trigger_type: str
    conditions: Dict[str, Any]
    actions: List[WorkflowAction]
    escalation: Optional[Dict[str, Any]] = None
    priority: int = 5
    enabled: bool = True


class ConnectorStatus(BaseModel):
    """Status of an integration connector."""
    name: str
    type: str
    status: str
    last_error: Optional[str]
    connected_at: Optional[str]


class ComplianceCheckRequest(BaseModel):
    """Request for compliance validation."""
    regulation: str
    check_type: str
    resource_id: str


class ComplianceCheckResult(BaseModel):
    """Result of a compliance check."""
    check_id: str
    regulation: str
    check_type: str
    passed: bool
    details: Dict[str, Any]
    severity: str
    remediation: Optional[str]
    timestamp: str