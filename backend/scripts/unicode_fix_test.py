#!/usr/bin/env python3
"""Fix Unicode console export issue on Windows."""
import sys
import os

# Force UTF-8 encoding for stdout/stderr at the lowest level
if sys.platform.startswith('win'):
    # Reconfigure stdout and stderr to use UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    # Also set the environment variable
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import torch
import torch.nn as nn

class SimpleModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(10, 1)
    
    def forward(self, x):
        return self.linear(x)

def test_export():
    model = SimpleModel()
    model.eval()
    dummy = torch.randn(1, 10)
    
    try:
        # Try exporting with verbose=False to minimize output
        torch.onnx.export(
            model, 
            dummy, 
            "simple_test.onnx",
            verbose=False,  # This might reduce the problematic logging
            export_params=True,
            opset_version=11,
            do_constant_folding=True
        )
        print("SUCCESS: Simple model exported")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

if __name__ == "__main__":
    success = test_export()
    sys.exit(0 if success else 1)