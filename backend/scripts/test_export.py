#!/usr/bin/env python3
"""Test script to export just the spoof detector model."""
import os
import sys
import logging
from pathlib import Path

# Configure logging to avoid Unicode issues on Windows
if sys.platform.startswith('win'):
    # Remove any existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Add a handler that doesn't use Unicode
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)

# Redirect stdout/stderr to avoid Unicode issues with torch
original_stdout = sys.stdout
original_stderr = sys.stdout

import torch
import torch.onnx

def export_spoof_detector_onnx():
    """Export simple spoof CNN to ONNX."""
    # Add the app/models directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "models"))
    
    try:
        from spoof_detector import SpoofNet
        logging.info("Successfully imported SpoofNet")
    except Exception as e:
        logging.error(f"Failed to import SpoofNet: {e}")
        return False
    
    model = SpoofNet()
    model.eval()
    dummy_input = torch.randn(1, 3, 64, 64)
    
    # Try export with minimal settings
    try:
        # Temporarily redirect stdout/stderr to avoid Unicode issues
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        
        torch.onnx.export(
            model,
            dummy_input,
            "spoof_detector_test.onnx",
            export_params=True,
            opset_version=11,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['spoof_score']
        )
        
        # Restore redirects
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        
        logging.info("Successfully exported spoof_detector.onnx")
        return True
    except Exception as e:
        # Restore redirects
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        
        logging.error(f"Failed to export model: {e}")
        # Try with even simpler settings
        try:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            
            torch.onnx.export(
                model,
                dummy_input,
                "spoof_detector_test.onnx"
            )
            
            # Restore redirects
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            
            logging.info("Successfully exported spoof_detector.onnx with default settings")
            return True
        except Exception as e2:
            # Restore redirects
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            
            logging.error(f"Failed even with default settings: {e2}")
            return False

if __name__ == "__main__":
    success = export_spoof_detector_onnx()
    sys.exit(0 if success else 1)