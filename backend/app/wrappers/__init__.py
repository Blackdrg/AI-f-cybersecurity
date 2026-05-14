"""
Wrapper abstraction layer for external services and models.
"""
from .adapters import BaseAdapter, AdapterConfig, AdapterRegistry
from .service_wrappers import ServiceWrapper, ModelWrapper, CacheWrapper, RateLimitWrapper
from .model_wrappers import ModelAdapter, FaceRecognitionWrapper, SpoofDetectionWrapper

__all__ = [
    "BaseAdapter",
    "AdapterConfig",
    "AdapterRegistry",
    "ServiceWrapper",
    "ModelWrapper",
    "CacheWrapper",
    "RateLimitWrapper",
    "ModelAdapter",
    "FaceRecognitionWrapper",
    "SpoofDetectionWrapper",
]