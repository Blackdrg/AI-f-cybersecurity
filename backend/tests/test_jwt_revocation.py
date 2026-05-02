
"""Tests for JWT distributed revocation system"""
import pytest
import asyncio
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch
from app.middleware.authentication import DistributedJWTRevocationStore

@pytest.mark.asyncio
async def test_jwt_revocation_store_connection():
    store = DistributedJWTRevocationStore()
    store._initialized = False
    store.client = None
    with patch("redis.asyncio.from_url", side_effect=Exception("Connection failed")):
        await store.ensure_connected()
        assert store._initialized == False
        assert store.client is None
    assert await store.is_revoked("test_jti") == False


@pytest.mark.asyncio
async def test_jwt_revocation_flow():
    store = DistributedJWTRevocationStore()
    await store._ensure_client()
    assert store._initialized == True
    
    now = int(time.time())
    exp = now + 3600
    jti = "test-jti-12345"
    
    result = await store.revoke_token(jti, exp)
    assert result == True
    
    assert await store.is_revoked(jti) == True
    
    info = await store.get_revocation_info(jti)
    assert info is not None
    assert info["jti"] == jti
    assert info["revoked"] == True
    assert info["expires_at"] == exp


@pytest.mark.asyncio
async def test_batch_revocation():
    store = DistributedJWTRevocationStore()
    await store._ensure_client()
    
    jtis = ["jti-1", "jti-2", "jti-3"]
    exp = int(time.time()) + 3600
    result = await store.revoke_token_batch(jtis, exp)
    
    assert result["success"] == True
    assert result["revoked"] == 3
    
    for jti in jtis:
        assert await store.is_revoked(jti) == True


@pytest.mark.asyncio
async def test_token_introspection():
    store = DistributedJWTRevocationStore()
    await store._ensure_client()
    
    # Test non-revoked token
    assert await store.is_revoked("test-jti-456") == False
    assert await store.get_revocation_info("test-jti-456") is None
    
    # Test revoked token
    jti = "test-jti-456"
    exp = int(time.time()) + 3600
    await store.revoke_token(jti, exp)
    
    assert await store.is_revoked(jti) == True
    info = await store.get_revocation_info(jti)
    assert info is not None
    assert info["jti"] == jti
    assert info["revoked"] == True
    assert info["ttl_remaining"] == 3600


@pytest.mark.asyncio
async def test_revocation_on_uninitialized_store():
    """Test behavior when Redis is not available."""
    store = DistributedJWTRevocationStore()
    store._initialized = False
    store.client = None
    
    # Should return False for revoked check when not initialized
    assert await store.is_revoked("any_jti") == False
    
    # Should return None for info when not initialized
    info = await store.get_revocation_info("any_jti")
    assert info is None


@pytest.mark.asyncio
async def test_revoke_token_error_handling():
    """Test that errors during revocation are handled gracefully."""
    store = DistributedJWTRevocationStore()
    await store._ensure_client()
    
    # Test with invalid expiration (in the past)
    now = int(time.time())
    exp_past = now - 3600
    jti = "expired-jti-test"
    
    # Should still succeed even with past expiration
    result = await store.revoke_token(jti, exp_past)
    assert result == True

