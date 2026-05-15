#!/usr/bin/env python3
"""Super simple test to isolate the export issue."""
import os
import sys
import torch
import torch.nn as nn

# Set environment to avoid torch export logging issues
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

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
        torch.onnx.export(model, dummy, "simple_test.onnx")
        print("SUCCESS: Simple model exported")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

if __name__ == "__main__":
    success = test_export()
    sys.exit(0 if success else 1)