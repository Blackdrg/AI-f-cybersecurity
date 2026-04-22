import os
import platform
import torch
import onnxruntime as ort
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

def detect_edge_device() -> str:
    """Detect device type: jetson/cpu/gpu."""
    uname = platform.uname()
    if 'tegra' in uname.release.lower():
        return 'jetson'
    if torch.cuda.is_available():
        return 'gpu'
    return 'cpu'

class EdgeAdapter:
    """Model runtime adapter for edge devices."""
    
    def __init__(self):
        self.device_type = detect_edge_device()
        self.providers = self._get_providers()
        logger.info(f"Edge device detected: {self.device_type}, providers: {self.providers}")
    
    def _get_providers(self) -> list:
        if self.device_type == 'jetson':
            # Jetson Nano CUDA/ARM
            return ['CUDAExecutionProvider', 'CPUExecutionProvider']
        elif self.device_type == 'gpu':
            return ['CUDAExecutionProvider']
        else:
            return ['CPUExecutionProvider']
    
    def load_onnx_model(self, model_path: str) -> ort.InferenceSession:
        """Load ONNX model with optimal providers."""
        session = ort.InferenceSession(model_path, providers=self.providers)
        return session
    
    def get_device_config(self) -> Dict:
        """Get runtime config."""
        return {
            'device': self.device_type,
            'providers': self.providers,
            'onnx': True,
            'batch_size': 8 if self.device_type == 'jetson' else 32
        }

# Global adapter
_edge_adapter = EdgeAdapter()

def get_edge_adapter():
    return _edge_adapter

