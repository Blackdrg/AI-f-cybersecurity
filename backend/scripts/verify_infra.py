#!/usr/bin/env python3
"""Verify all infrastructure dependencies are properly configured."""
import os
import sys
import asyncio
from pathlib import Path

# Load .env file if exists
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)

def check_env_vars():
    """Check required environment variables."""
    print("\n=== Environment Variables Check ===")
    
    required = {
        'JWT_SECRET': 'JWT secret key for authentication',
        'ENCRYPTION_KEY': 'AES-256 encryption key for biometrics',
    }
    
    optional = {
        'STRIPE_SECRET_KEY': 'Stripe payment processing',
        'STRIPE_WEBHOOK_SECRET': 'Stripe webhook verification',
        'OPENAI_API_KEY': 'OpenAI GPT models',
        'AZURE_TENANT_ID': 'Azure AD OAuth',
        'AZURE_CLIENT_ID': 'Azure AD OAuth',
        'AZURE_CLIENT_SECRET': 'Azure AD OAuth',
        'GOOGLE_CLIENT_ID': 'Google OAuth',
        'GOOGLE_CLIENT_SECRET': 'Google OAuth',
        'BING_API_KEY': 'Bing search for OSINT',
        'AWS_REGION': 'AWS KMS configuration',
        'AWS_KMS_KEY_ID': 'AWS KMS key for encryption',
    }
    
    missing_required = []
    
    for var, desc in required.items():
        val = os.getenv(var)
        if val:
            print(f"  [OK] {var}: Set ({desc})")
        else:
            print(f"  [MISSING] {var}: MISSING ({desc})")
            missing_required.append(var)
    
    print("\nOptional Configuration:")
    for var, desc in optional.items():
        val = os.getenv(var)
        status = "Set" if val else "Not set (optional)"
        symbol = "[OK]" if val else "[--]"
        print(f"  {symbol} {var}: {status} ({desc})")
    
    return len(missing_required) == 0

def check_onnx_models():
    """Check ONNX model bundle."""
    print("\n=== ONNX Models Check ===")
    
    bundle_path = Path(__file__).parent.parent / "models" / "onnx_bundle"
    
    required_models = [
        'spoof_detector.onnx',
        'behavioral_predictor.onnx',
        'deepfake_detector.onnx',
        'face_reconstructor.onnx',
        'gaitset.onnx',
    ]
    
    all_present = True
    for model in required_models:
        model_path = bundle_path / model
        if model_path.exists() and model_path.stat().st_size > 100:
            print(f"  [OK] {model}: Present ({model_path.stat().st_size} bytes)")
        else:
            print(f"  [MISSING] {model}: MISSING or empty")
            all_present = False
    
    return all_present

def check_geoip():
    """Check GeoIP database."""
    print("\n=== GeoIP Database Check ===")
    
    paths = [
        Path(__file__).parent.parent / "data" / "GeoLite2-City.mmdb",
        Path("/app/data/GeoLite2-City.mmdb"),
        Path.home() / "data" / "GeoLite2-City.mmdb",
    ]
    
    for p in paths:
        if p.exists():
            print(f"  [OK] GeoIP database found: {p}")
            return True
    
    print("  [--] GeoIP database not found (optional - geo-restriction will be disabled)")
    return True  # Not critical

async def check_database():
    """Check PostgreSQL connection."""
    print("\n=== PostgreSQL Check ===")
    
    try:
        import asyncpg
        
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = int(os.getenv('DB_PORT', 5432))
        db_name = os.getenv('DB_NAME', 'face_recognition')
        db_user = os.getenv('DB_USER', 'postgres')
        db_pass = os.getenv('DB_PASSWORD', 'password')
        
        print(f"  Attempting connection to {db_host}:{db_port}/{db_name}...")
        
        conn = await asyncpg.connect(
            host=db_host, port=db_port,
            database=db_name, user=db_user,
            password=db_pass,
            timeout=5
        )
        
        # Check pgvector extension
        result = await conn.fetchval("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        if result:
            print("  [OK] pgvector extension installed")
        else:
            print("  [WARNING] pgvector extension NOT installed")
        
        await conn.close()
        print("  [OK] PostgreSQL connection successful")
        return True
        
    except Exception as e:
        print(f"  [FAILED] PostgreSQL connection failed: {e}")
        return False

async def check_redis():
    """Check Redis connection."""
    print("\n=== Redis Check ===")
    
    try:
        import redis.asyncio as redis
        
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        client = redis.from_url(redis_url)
        
        await client.ping()
        print(f"  [OK] Redis connection successful: {redis_url}")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"  [FAILED] Redis connection failed: {e}")
        return False

def check_dependencies():
    """Check Python dependencies."""
    print("\n=== Python Dependencies Check ===")
    
    deps = [
        ('fastapi', 'FastAPI web framework'),
        ('uvicorn', 'ASGI server'),
        ('asyncpg', 'PostgreSQL async driver'),
        ('pgvector', 'Vector similarity search'),
        ('redis', 'Redis client'),
        ('celery', 'Task queue'),
        ('stripe', 'Payment processing'),
        ('openai', 'OpenAI API client'),
        ('onnxruntime', 'ONNX inference'),
        ('GeoIP', 'GeoIP database support'),
    ]
    
    missing = []
    for pkg, desc in deps:
        try:
            __import__(pkg)
            print(f"  [OK] {pkg}: Installed ({desc})")
        except ImportError:
            print(f"  [MISSING] {pkg}: NOT installed ({desc})")
            missing.append(pkg)
    
    return len(missing) == 0

async def main():
    print("=" * 50)
    print("AI-F Infrastructure Verification")
    print("=" * 50)
    
    # Run checks
    env_ok = check_env_vars()
    onnx_ok = check_onnx_models()
    geoip_ok = check_geoip()
    deps_ok = check_dependencies()
    
    db_ok = await check_database()
    redis_ok = await check_redis()
    
    # Summary
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    
    checks = [
        ("Environment Variables", env_ok),
        ("ONNX Models", onnx_ok),
        ("GeoIP Database", geoip_ok),
        ("Python Dependencies", deps_ok),
        ("PostgreSQL", db_ok),
        ("Redis", redis_ok),
    ]
    
    all_passed = True
    for name, passed in checks:
        status = "[OK] PASS" if passed else "[FAILED] FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n[SUCCESS] All infrastructure checks passed!")
        return 0
    else:
        print("\n[WARNING] Some infrastructure checks failed. See above for details.")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))