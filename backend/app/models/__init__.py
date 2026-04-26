"""
Biometric Recognition Models Package.

Includes all ML models and utility modules for identity recognition.
"""

# Core models
from .face_detector import FaceDetector
from .face_embedder import FaceEmbedder
from .face_reconstructor import FaceReconstructor
from .spoof_detector import SpoofDetector
from .emotion_detector import EmotionDetector
from .age_gender_estimator import AgeGenderEstimator
from .behavioral_predictor import BehavioralPredictor
from .gait_analyzer import GaitAnalyzer
from .voice_embedder import VoiceEmbedder

# Advanced security models
from .enhanced_spoof import (
    SpoofResult,
    ChallengeResponseVerifier,
    TemporalAnalyzer
)
from .model_calibrator import ModelCalibrator
from .bias_detector import BiasDetector
from .ethical_governor import EthicalGovernor
from .crypto_attestation import CryptoAttestation

# Next-gen identity features
from .homomorphic_encryption import (
    HomomorphicEncryptionEngine,
    HomomorphicVectorStore
)
from .mpc_matching import (
    MPCIdentityMatcher,
    FederatedIdentityRegistry,
    PrivateSetIntersection,
    BloomFilter,
    SecureScalarProduct
)
from .did_identity import (
    DIDManager,
    SecureEnclaveWallet,
    DIDKeyManager,
    DIDDocument,
    VerifiableCredential
)
from .revocable_tokens import (
    RevocableTokenManager,
    TokenRevocationRegistry,
    RevocableToken,
    TokenType,
    TokenMetadata
)
from .zkp_audit_trails import (
    AuditTrail,
    ZKProofGenerator,
    AuditEvent,
    ZKPAuditProof
)
from .cross_border_privacy import (
    PrivacyPolicyEngine,
    ProcessingDecision,
    GeoIPResolver,
    Jurisdiction,
    PrivacyLaw,
    RegionalPolicy
)

# Explainable AI & monitoring
from .explainable_ai import (
    DecisionBreakdownEngine,
    ExplainableDecision,
    DecisionFactor,
    AttributionMap,
    CounterfactualExplanation,
    CalibrationPoint,
    BiasMetrics,
    ConfidenceCalibrator,
    BiasAuditor,
    decision_breakdown_engine
)
from .continuous_monitoring import (
    PrivacyAwareSessionManager,
    SessionContinuityTracker,
    SessionContext,
    BehavioralDrift,
    PassiveReauthManager
)

# Deepfake defense
from .enhanced_spoof import (
    DeepfakeDetector,
    DeepfakeThreatIntelligence,
    WatermarkDetector,
    SyntheticRiskModel,
    enhanced_spoof_detector
)

# Emotion + Behavior Layer
from .emotion_behavior import (
    EmotionBehaviorEngine,
    EmotionDetector as BehaviorEmotionDetector,
    BehaviorTracker,
    RulesEngine,
    get_emotion_behavior_engine,
    analyze_recognition_with_behavior
)

__all__ = [
    # Core models
    'FaceDetector',
    'FaceEmbedder',
    'FaceReconstructor',
    'SpoofDetector',
    'EmotionDetector',
    'AgeGenderEstimator',
    'BehavioralPredictor',
    'GaitAnalyzer',
    'VoiceEmbedder',
    
    # Advanced security
    'EnhancedSpoofDetector',
    'ChallengeResponseVerifier',
    'TemporalAnalyzer',
    'ModelCalibrator',
    'BiasDetector',
    'EthicalGovernor',
    'CryptoAttestation',
    
    # Next-gen identity
    'HomomorphicEncryptionEngine',
    'HomomorphicVectorStore',
    'MPCIdentityMatcher',
    'FederatedIdentityRegistry',
    'DIDManager',
    'SecureEnclaveWallet',
    'RevocableTokenManager',
    'AuditTrail',
    'PrivacyPolicyEngine',
    
    # Explainable AI
    'DecisionBreakdownEngine',
    'ExplainableDecision',
    'ConfidenceCalibrator',
    'BiasAuditor',
    'decision_breakdown_engine',
    
    # Monitoring
    'PrivacyAwareSessionManager',
    'SessionContinuityTracker',
    
    # Deepfake defense
    'DeepfakeDetector',
    'DeepfakeThreatIntelligence',
    'WatermarkDetector',
    'SyntheticRiskModel',
    'enhanced_spoof_detector',
    
    # Emotion + Behavior Layer
    'EmotionBehaviorEngine',
    'BehaviorEmotionDetector',
    'BehaviorTracker',
    'RulesEngine',
    'get_emotion_behavior_engine',
    'analyze_recognition_with_behavior'
]