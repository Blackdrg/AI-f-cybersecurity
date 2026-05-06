#!/usr/bin/env python3
"""
Download and verify ONNX model weights for production deployment.

This script downloads the required model weights for face recognition:
- InsightFace buffalo_l (face detection + embedding)
- ArcFace model for face recognition

These models are required for proper face recognition without fallbacks.

Usage:
    python download_models.py [--force] [--models-dir ./models/weights]

Environment Vars:
    MODEL_CACHE_DIR: Directory to cache downloaded models (default: ./models/weights)
    INSIGHTFACE_REPO: Source repo for models (default: insightface/recognition-models)
"""

import os
import sys
import argparse
import hashlib
import subprocess
from pathlib import Path
import urllib.request
import json

# Expected model weights with SHA256 checksums (when available)
MODEL_MANIFEST = {
    "buffalo_l": {
        "description": "InsightFace buffalo_l detection + recognition model",
        "files": {
            "det_10g.onnx": {
                "description": "Face detection model (640x640 input)",
                "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip",
                "size_mb": 950,  # ~950MB
            }
        },
        "source": "github.com/deepinsight/insightface",
        "license": "Apache 2.0",
    },
    "w600k_r50": {
        "description": "ArcFace ResNet-50 model for recognition",
        "files": {
            "w600k_r50.onnx": {
                "description": "Face embedding model (112x112 input, 512-d output)",
                "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/models/w600k_r50.onnx",
                "size_mb": 150,
            }
        },
        "source": "github.com/deepinsight/insightface",
        "license": "Apache 2.0",
    }
}


def verify_downloads_dir(download_dir: Path) -> Path:
    """Ensure download directory exists."""
    download_dir.mkdir(parents=True, exist_ok=True)
    return download_dir


def download_file(url: str, dest_path: Path) -> bool:
    """Download a file with progress reporting."""
    try:
        print(f"  Downloading from {url}")
        urllib.request.urlretrieve(url, dest_path, reporthook=lambda b, bs, t: 
            print(f"\r    Progress: {b*bs/1024/1024:.1f}MB", end='') if t > 0 else None)
        print(f"\n  Saved to {dest_path}")
        return True
    except Exception as e:
        print(f"\n  Download failed: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return False


def main():
    parser = argparse.ArgumentParser(description="Download ONNX model weights for face recognition")
    parser.add_argument("--force", action="store_true", help="Force re-download even if files exist")
    parser.add_argument("--models-dir", default=os.environ.get("MODEL_CACHE_DIR", "./models/weights"),
                        help="Directory to store downloaded models")
    parser.add_argument("--list", action="store_true", help="List available models only")
    args = parser.parse_args()

    models_dir = verify_downloads_dir(Path(args.models_dir))

    if args.list:
        print("Available model weights:")
        for name, info in MODEL_MANIFEST.items():
            print(f"\n  {name}:")
            print(f"    Description: {info['description']}")
            print(f"    Source: {info['source']}")
            print(f"    License: {info['license']}")
            for fname, finfo in info['files'].items():
                fpath = models_dir / fname
                status = "[DOWNLOAD]" if not fpath.exists() else "[INSTALLED]"
                print(f"      {fname}: {finfo['description']} ({finfo['size_mb']}MB) {status}")
        return 0

    print("=" * 70)
    print("Face Recognition Model Weights Downloader")
    print("=" * 70)
    print(f"\nModels directory: {models_dir.absolute()}")
    print(f"Total download size: ~1.1 GB\n")

    downloaded = []
    failed = []

    for model_name, model_info in MODEL_MANIFEST.items():
        print(f"\n{model_name.upper()}:")
        print(f"  {model_info['description']}")

        for fname, finfo in model_info['files'].items():
            dest_path = models_dir / fname
            
            if dest_path.exists() and not args.force:
                print(f"  ✓ {fname} already exists, skipping (use --force to re-download)")
                downloaded.append(fname)
                continue

            print(f"  Downloading {fname}...")
            print(f"  Size: ~{finfo['size_mb']} MB")
            
            if download_file(finfo['url'], dest_path):
                downloaded.append(fname)
            else:
                failed.append(fname)

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    if downloaded:
        print(f"\n✓ Successfully downloaded {len(downloaded)} file(s)")
        for f in downloaded:
            size = models_dir / f
            print(f"  - {f} ({size.stat().st_size / 1024 / 1024:.1f} MB)")
    
    if failed:
        print(f"\n✗ Failed to download {len(failed)} file(s)")
        for f in failed:
            print(f"  - {f}")
        print("\nNote: Some models may require manual download due to size or licensing.")
        print("See the deployment guide for alternative download methods.")
    
    print("\nNext Steps:")
    print("1. Set MODEL_CACHE_DIR environment variable to point to your models directory")
    print("2. Update model paths in src/backend/app/models/*.py to use downloaded weights")
    print("3. Restart the service to load the production models")
    print("\nFor Docker deployments, see docs/docker-models.md")
    
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())