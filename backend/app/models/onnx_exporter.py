"""
ONNX Export Pipeline
Convert PyTorch models to ONNX format for edge deployment
"""
import os
import torch
import onnx
import logging
from typing import Dict, Optional, Tuple, List
from pathlib import Path

logger = logging.getLogger(__name__)

class ONNXExporter:
    """Export trained PyTorch models to ONNX with optimization"""
    
    def __init__(self, models_dir: str = "/app/models", export_dir: str = "/app/models/onnx"):
        self.models_dir = Path(models_dir)
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    def export_model(self, model_name: str, model: torch.nn.Module, 
                     input_shape: Tuple[int, ...], output_names: List[str] = None,
                     opset_version: int = 14, dynamic_axes: Dict = None) -> str:
        """
        Export a PyTorch model to ONNX.
        
        Args:
            model_name: Name of model ('face_embedder', etc.)
            model: Instantiated PyTorch model (should be eval mode)
            input_shape: Example input shape (batch, channels, height, width)
            output_names: Names for output tensors
            opset_version: ONNX opset (14 recommended)
            dynamic_axes: Dict specifying dynamic axes (e.g., batch)
        
        Returns:
            Path to exported ONNX file
        """
        model.eval()
        
        # Create dummy input
        dummy_input = torch.randn(input_shape)
        
        # Build output path
        onnx_path = self.export_dir / f"{model_name}.onnx"
        
        # Dynamic axes default: batch dimension
        if dynamic_axes is None:
            dynamic_axes = {'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
        
        # Export
        torch.onnx.export(
            model,
            dummy_input,
            str(onnx_path),
            export_params=True,
            opset_version=opset_version,
            do_constant_folding=True,
            input_names=['input'],
            output_names=output_names or ['output'],
            dynamic_axes=dynamic_axes,
            verbose=False
        )
        
        # Verify model
        onnx_model = onnx.load(str(onnx_path))
        onnx.checker.check_model(onnx_model)
        
        logger.info(f"Exported {model_name} to ONNX: {onnx_path} ({onnx_path.stat().st_size} bytes)")
        
        # Optimize (optional)
        try:
            from onnxruntime.transformers import optimizer
            # Could apply optimizations here
        except ImportError:
            pass
        
        return str(onnx_path)
    
    def export_all_models(self, model_registry: Dict[str, torch.nn.Module]) -> Dict[str, str]:
        """
        Export all models in registry to ONNX.
        
        Returns:
            Dict mapping model_name -> onnx_path
        """
        exported = {}
        
        # Define shapes per model
        shapes = {
            'face_embedder': (1, 3, 112, 112),
            'face_detector': (1, 3, 224, 224),
            'spoof_detector': (1, 3, 224, 224),
            'emotion_detector': (1, 1, 48, 48),
            'age_gender_estimator': (1, 3, 112, 112),
            'voice_embedder': (1, 1, 16000),  # 1 sec audio at 16kHz
        }
        
        for name, model in model_registry.items():
            if name in shapes:
                try:
                    path = self.export_model(name, model, shapes[name])
                    exported[name] = path
                except Exception as e:
                    logger.error(f"Failed to export {name}: {e}")
            else:
                logger.warning(f"No ONNX export config for {name}")
        
        return exported
    
    def benchmark_onnx_model(self, onnx_path: str, input_shape: Tuple, iterations: int = 100) -> Dict[str, float]:
        """Benchmark ONNX model inference speed"""
        import onnxruntime as ort
        
        # Create session
        session = ort.InferenceSession(onnx_path, providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        input_name = session.get_inputs()[0].name
        
        # Warm-up
        dummy = torch.randn(input_shape).numpy()
        for _ in range(10):
            session.run(None, {input_name: dummy})
        
        # Benchmark
        import time
        start = time.time()
        for _ in range(iterations):
            session.run(None, {input_name: dummy})
        total = time.time() - start
        
        avg_ms = (total / iterations) * 1000
        return {
            "iterations": iterations,
            "total_seconds": total,
            "average_ms": avg_ms,
            "model": onnx_path
        }


# Global exporter
onnx_exporter = ONNXExporter()
