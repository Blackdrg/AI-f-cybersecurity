from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID


class EnrollRequest(BaseModel):
    name: Optional[str] = None
    metadata: Dict[str, Any] = {}
    consent: bool
    camera_id: Optional[str] = None
    voice_files: Optional[List[str]] = None  # Base64 encoded or file paths
    gait_video: Optional[str] = None  # Base64 encoded video
    # PPG, heart rate, etc.
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
    voice_file: Optional[str] = None  # For multi-modal
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
    action: str  # 'grant', 'revoke', 'view'
    biometric_type: Optional[str] = None  # 'face', 'voice', 'gait'


class ZKPRequest(BaseModel):
    proof: Dict[str, Any]
    challenge: str


class BiasReport(BaseModel):
    demographic_parity_difference: float
    equalized_odds_difference: float


class DeleteResponse(BaseModel):
    deleted: bool
    message: str


class MetricsResponse(BaseModel):
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
    device_id: str
    model_gradients: Dict[str, Any]  # Serialized gradients or model updates
    num_samples: int
    timestamp: str


class ModelVersion(BaseModel):
    version_id: str
    model_data: bytes  # Serialized model
    created_at: str
    description: Optional[str] = None


class EdgeDeviceRequest(BaseModel):
    device_id: str
    action: str  # 'register', 'update', 'status'
    model_version: Optional[str] = None


class MultiCameraRequest(BaseModel):
    camera_ids: List[str]
    sync_timestamps: List[str]
    streams: List[str]  # Base64 encoded streams or URLs


class OTADownload(BaseModel):
    device_id: str
    model_version: str


class AnalyticsResponse(BaseModel):
    # e.g., [{'date': '2023-01-01', 'recognitions': 100, 'enrollments': 10}]
    time_series: List[Dict[str, Any]]
    bias_trends: List[Dict[str, Any]]
    device_stats: List[Dict[str, Any]]


# SaaS Schemas
class UserCreate(BaseModel):
    email: str
    name: str
    subscription_tier: str = "free"


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


class SubscriptionCreate(BaseModel):
    plan_id: str


class SubscriptionResponse(BaseModel):
    subscription_id: str
    user_id: str
    plan_id: str
    status: str
    created_at: str
    expires_at: str


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


class UsageResponse(BaseModel):
    user_id: str
    period_start: str
    period_end: str
    recognitions_used: int
    enrollments_used: int
    recognitions_limit: int
    enrollments_limit: int


class AIAssistantRequest(BaseModel):
    query: str


class AIAssistantResponse(BaseModel):
    query: str
    response: str
    model_used: str


class SupportTicketCreate(BaseModel):
    subject: str
    description: str
    priority: str = "medium"


class SupportTicketUpdate(BaseModel):
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


# Public Enrichment Schemas
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
    # e.g., {"name": "John Doe", "email": "john@example.com"}
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


class AuditLogsResponse(BaseModel):
    logs: List[AuditLogEntry]
    total: int


class FlagForReviewRequest(BaseModel):
    reason: Optional[str] = None
