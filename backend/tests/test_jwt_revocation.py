
"""Tests for JWT distributed revocation system"""
import pytest
import asyncio
import time
import jwt
from unittest.mock import AsyncMock, patch, MagicMock
from app.middleware.authentication import DistributedJWTRevocationStore, get_jwt_revocation_store

@pytest.mark.asyncio
async def test_jwt_revocation_store_connection():
    store = DistributedJWTRevocationStore()
    with patch("redis.asyncio.from_url", side_effect=Exception("Connection failed")):
        await store.ensure_connected()
        assert store._initialized == False
        assert store.client is None
    assert await store.is_revoked("test_jti") == False

@pytest.mark.asyncio
async def test_jwt_revocation_flow():
    store = DistributedJWTRevocationStore()
    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)
    mock_client.exists = AsyncMock(return_value=0)
    mock_client.setex = AsyncMock(return_value=True)
    mock_client.get = AsyncMock(return_value=None)
    mock_client.ttl = AsyncMock(return_value=3600)
    with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_client)):
        await store.ensure_connected()
        assert store._initialized == True
        now = int(time.time())
        exp = now + 3600
        jti = "test-jti-12345"
        result = await store.revoke_token(jti, exp)
        assert result == True
        mock_client.exists = AsyncMock(return_value=1)
        assert await store.is_revoked(jti) == True
        mock_client.get = AsyncMock(return_value=str(exp))
        info = await store.get_revocation_info(jti)
        assert info is not None
        assert info["jti"] == jti
        assert info["revoked"] == True
        assert info["expires_at"] == exp

@pytest.mark.asyncio
async def test_batch_revocation():
    store = DistributedJWTRevocationStore()
    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)
    pipe_calls = []
    def record_setex(key, ttl, value):
        pipe_calls.append((key, ttl, value))
        return AsyncMock()
    mock_pipe = MagicMock()
    mock_pipe.setex = AsyncMock(side_effect=record_setex)
    async def execute():
        return [True, True, True]
    mock_pipe.execute = AsyncMock(side_effect=execute)
    mock_client.pipeline = MagicMock(return_value=mock_pipe)
    with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_client)):
        await store.ensure_connected()
        jtis = ["jti-1", "jti-2", "jti-3"]
        exp = int(time.time()) + 3600
        result = await store.revoke_token_batch(jtis, exp)
        assert result["success"] == True
        assert mock_pipe.execute.called

@pytest.mark.asyncio
async def test_token_introspection():
    store = DistributedJWTRevocationStore()
    assert await store.is_revoked("test-jti-456") == False
    assert await store.get_revocation_info("test-jti-456") is None
    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)
    mock_client.exists = AsyncMock(return_value=0)
    mock_client.setex = AsyncMock(return_value=True)
    mock_client.get = AsyncMock(return_value=str(int(time.time()) + 3600))
    mock_client.ttl = AsyncMock(return_value=3600)
    with patch("redis.asyncio.from_url", AsyncMock(return_value=mock_client)):
        await store.ensure_connected()
        jti = "test-jti-456"
        exp = int(time.time()) + 3600
        assert await store.is_revoked(jti) == False
        await store.revoke_token(jti, exp)
        mock_client.exists = AsyncMock(return_value=1)
        assert await store.is_revoked(jti) == True
        info = await store.get_revocation_info(jti)
        assert info is not None
        assert info["jti"] == jti
        assert info["revoked"] == True
        assert info["ttl_remaining"] == 3600

