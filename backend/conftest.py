"""Comprehensive pytest fixtures to unblock all extended tests.

This conftest replaces the previous version by applying all necessary
mocks at import time (before the FastAPI app is created). It provides:
- In‑memory database (no PostgreSQL required)
- Fake Redis for all Redis‑backed features
- Mock Stripe, OpenAI, OAuth, GeoIP, ONNX, InsightFace, etc.
- Test client fixture and helpers
"""

import os
import sys
import uuid
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

# =============================================================================
# Environment configuration (set BEFORE any app imports)
# =============================================================================
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ.setdefault('JWT_SECRET', 'test-jwt-secret-key-64byte-long-string-here-for-HS256')
os.environ.setdefault('ENCRYPTION_KEY', '0XKYdoZg1Q4f1mXPIWwEVRwQcGm0sKomFk4N5ksJ2nA=')
os.environ.setdefault('OPENAI_API_KEY', 'sk-test-mock-openai')
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_mock_stripe')
os.environ.setdefault('STRIPE_WEBHOOK_SECRET', 'whsec_change_me')  # matches test_webhooks
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('CI', 'true')
os.environ.setdefault('MODEL_CACHE_DIR', '/tmp/models')
os.environ.setdefault('FRONTEND_URL', 'http://localhost:3000')
# OAuth (so get_oauth_provider doesn't raise)
os.environ.setdefault('AZURE_TENANT_ID', 'test-tenant')
os.environ.setdefault('AZURE_CLIENT_ID', 'test-azure-client-id')
os.environ.setdefault('AZURE_CLIENT_SECRET', 'test-azure-client-secret')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'test-google-client-id')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'test-google-secret')

# =============================================================================
# Global in‑memory database mock
# =============================================================================
class MockConnection:
    """Async context manager that mimics a DB connection."""
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def fetch(self, query, *args):
        return []          # Empty result set for SELECTs

    async def fetchrow(self, query, *args):
        return None       # No single row

    async def execute(self, query, *args):
        return None       # OK

class MockPool:
    """Mock connection pool that supports async with acquire()."""
    def acquire(self):
        class AcquireContext:
            async def __aenter__(self):
                return MockConnection()
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        return AcquireContext()

class InMemoryDB:
    """A minimal async DB client used by the entire test suite."""
    def __init__(self):
        self.reset()
        self.pool = MockPool()

    def reset(self):
        # Storage dictionaries
        self._users = {}
        self._persons = {}
        self._subscriptions = {}          # by subscription_id
        self._subscriptions_by_user = {}  # user_id -> [sub, ...]
        self._payments = []
        self._audit_log = []
        self._support_tickets = {}

    # -------------------------------------------------------------------------
    # User management
    # -------------------------------------------------------------------------
    async def create_user(self, user_id, email, name, subscription_tier='free'):
        self._users[user_id] = {
            'user_id': user_id,
            'email': email,
            'name': name,
            'subscription_tier': subscription_tier,
            'created_at': datetime.utcnow()
        }
        return True

    async def get_user_by_id(self, user_id):
        return self._users.get(user_id)

    async def get_user_by_email(self, email):
        for u in self._users.values():
            if u.get('email') == email:
                return u
        return None

    async def update_user(self, user_id, email=None, name=None, subscription_tier=None):
        user = self._users.get(user_id)
        if not user:
            return False
        if email is not None:
            user['email'] = email
        if name is not None:
            user['name'] = name
        if subscription_tier is not None:
            user['subscription_tier'] = subscription_tier
        return True

    async def delete_user(self, user_id):
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False

    # -------------------------------------------------------------------------
    # Subscription / billing
    # -------------------------------------------------------------------------
    async def create_subscription(self, subscription_id, user_id, plan_id, status='pending', starts_at=None, expires_at=None):
        sub = {
            'subscription_id': subscription_id,
            'user_id': user_id,
            'plan_id': plan_id,
            'status': status,
            'starts_at': starts_at,
            'expires_at': expires_at
        }
        self._subscriptions[subscription_id] = sub
        self._subscriptions_by_user.setdefault(user_id, []).append(sub)
        return True

    async def get_subscription(self, user_id):
        subs = self._subscriptions_by_user.get(user_id, [])
        return subs[-1] if subs else None

    async def get_subscription_history(self, user_id):
        return list(self._subscriptions_by_user.get(user_id, []))

    async def update_subscription(self, subscription_id, user_id=None, plan_id=None, status=None, **kwargs):
        sub = self._subscriptions.get(subscription_id)
        if sub:
            if user_id is not None:
                sub['user_id'] = user_id
            if plan_id is not None:
                sub['plan_id'] = plan_id
            if status is not None:
                sub['status'] = status
        return True

    async def cancel_subscription(self, subscription_id):
        sub = self._subscriptions.get(subscription_id)
        if sub:
            sub['status'] = 'cancelled'
        return True

    async def get_plan_by_id(self, plan_id):
        plans = {
            'free': {
                'plan_id': 'free',
                'name': 'Free Tier',
                'price': 0,
                'limits': {'recognitions': 100, 'enrollments': 10}
            },
            'pro': {
                'plan_id': 'pro',
                'name': 'Pro Tier',
                'price': 29.99,
                'limits': {'recognitions': 5000, 'enrollments': 500}
            },
            'enterprise': {
                'plan_id': 'enterprise',
                'name': 'Enterprise',
                'price': 99.99,
                'limits': {'recognitions': -1, 'enrollments': -1}
            }
        }
        return plans.get(plan_id, plans['free'])

    async def get_usage(self, user_id):
        """Return usage counters for the specified user."""
        sub = await self.get_subscription(user_id)
        if sub and sub.get('plan_id') == 'enterprise':
            limits = {'recognitions': -1, 'enrollments': -1}
        else:
            plan = await self.get_plan_by_id(sub.get('plan_id') if sub else 'free')
            limits = plan.get('limits', {'recognitions': 100, 'enrollments': 10})
        return {
            'user_id': user_id,
            'period_start': None,
            'period_end': None,
            'recognitions_used': 0,
            'enrollments_used': 0,
            'recognitions_limit': limits['recognitions'],
            'enrollments_limit': limits['enrollments']
        }

    async def get_monthly_usage(self, customer_id):
        return {'recognitions': 0, 'enrollments': 0}

    async def log_payment(self, user_id, amount, currency, status, stripe_payment_id=None, metadata=None):
        self._payments.append({
            'payment_id': str(uuid.uuid4()),
            'user_id': user_id,
            'amount': amount,
            'currency': currency,
            'status': status,
            'stripe_payment_id': stripe_payment_id,
            'metadata': metadata,
            'created_at': datetime.utcnow()
        })
        return True

    async def get_payment_history(self, user_id=None, limit=10):
        if user_id:
            results = [p for p in self._payments if p.get('user_id') == user_id]
        else:
            results = self._payments
        return results[:limit]

    async def log_audit_event(self, *args, **kwargs):
        self._audit_log.append({'args': args, 'kwargs': kwargs})
        return True

    async def get_user_by_stripe_customer(self, stripe_customer_id):
        for u in self._users.values():
            if u.get('stripe_customer_id') == stripe_customer_id:
                return u
        return None

    async def link_stripe_customer(self, user_id, stripe_customer_id):
        user = self._users.get(user_id)
        if user:
            user['stripe_customer_id'] = stripe_customer_id
            return True
        return False

    async def downgrade_to_free_tier(self, user_id):
        user = self._users.get(user_id)
        if user:
            user['subscription_tier'] = 'free'
            return True
        return False

    async def deactivate_subscription(self, subscription_id):
        sub = self._subscriptions.get(subscription_id)
        if sub:
            sub['status'] = 'cancelled'
        return True

    async def update_subscription_plan(self, subscription_id, plan_id):
        sub = self._subscriptions.get(subscription_id)
        if sub:
            sub['plan_id'] = plan_id
            return True
        return False

    async def extend_subscription(self, subscription_id, days):
        sub = self._subscriptions.get(subscription_id)
        if sub and sub.get('expires_at'):
            sub['expires_at'] = datetime.utcnow() + timedelta(days=days)
            return True
        return False

    async def mark_payment_failed(self, payment_id):
        for p in self._payments:
            if p.get('payment_id') == payment_id:
                p['status'] = 'failed'
                return True
        return False

    # -------------------------------------------------------------------------
    # Enrollment / recognition
    # -------------------------------------------------------------------------
    async def enroll_person(self, person_id, name, stored_embeddings, consent_record, camera_id=None, voice_embeddings=None, gait_embedding=None, age=None, gender=None):
        self._persons[person_id] = {
            'person_id': person_id,
            'name': name,
            'age': age,
            'gender': gender,
            'consent': consent_record,
            'camera_id': camera_id,
            'num_embeddings': len(stored_embeddings) if stored_embeddings else 0
        }
        return True

    async def recognize_faces(self, query_emb, top_k=1, threshold=0.0, camera_id=None, voice_embedding=None, gait_embedding=None):
        return []   # No matches in mock DB

    async def get_person(self, person_id):
        return self._persons.get(person_id)

    async def delete_person(self, person_id):
        if person_id in self._persons:
            del self._persons[person_id]
            return True
        return False

    async def submit_feedback(self, person_id, recognition_id, correct_person_id, confidence_score, feedback_type):
        return True

    # -------------------------------------------------------------------------
    # Generic query helpers (used by admin analytics, etc.)
    # -------------------------------------------------------------------------
    async def fetch(self, query, *args):
        return []

    async def fetchrow(self, query, *args):
        return None

    async def execute(self, query, *args):
        return None

    async def get_user_orgs(self, user_id):
        return []

    async def get_analytics(self, timeframe='24h'):
        return {'time_series': [], 'bias_trends': [], 'device_stats': []}

    async def get_active_edge_devices(self):
        return []

    # -------------------------------------------------------------------------
    # Support tickets
    # -------------------------------------------------------------------------
    async def create_ticket(self, ticket_id, user_id, subject, description, priority):
        self._support_tickets[ticket_id] = {
            'ticket_id': ticket_id,
            'user_id': user_id,
            'subject': subject,
            'description': description,
            'priority': priority,
            'status': 'open',
            'created_at': datetime.utcnow(),
            'updated_at': None
        }
        return True

    async def get_tickets(self, user_id):
        return [t for t in self._support_tickets.values() if t['user_id'] == user_id]

    async def get_ticket(self, ticket_id):
        return self._support_tickets.get(ticket_id)

    async def update_ticket(self, ticket_id, **kwargs):
        t = self._support_tickets.get(ticket_id)
        if t:
            t.update(kwargs)
            t['updated_at'] = datetime.utcnow()
            return True
        return False

# Instantiate a singleton mock DB
_mock_db = InMemoryDB()

def get_mock_db():
    return _mock_db

# =============================================================================
# Apply global patches (must happen BEFORE any import of app modules)
# =============================================================================

# --- Patch get_db and init_db ---
get_db_patcher = patch('app.db.db_client.get_db', side_effect=get_mock_db)
if os.environ.get('ENVIRONMENT') != 'integration':
    get_db_patcher.start()

async def _init_db_mock():
    pass
init_db_patcher = patch('app.db.db_client.init_db', side_effect=_init_db_mock)
if os.environ.get('ENVIRONMENT') != 'integration':
    init_db_patcher.start()

# --- Mock Redis ---
try:
    from fakeredis import AsyncFakeRedis
except ImportError:  # pragma: no cover
    AsyncFakeRedis = MagicMock

def _fake_redis_from_url(url, *args, **kwargs):
    return AsyncFakeRedis()

redis_async_patcher = patch('redis.asyncio.from_url', side_effect=_fake_redis_from_url)
if os.environ.get('ENVIRONMENT') != 'integration':
    redis_async_patcher.start()
redis_sync_patcher = patch('redis.from_url', side_effect=_fake_redis_from_url)
if os.environ.get('ENVIRONMENT') != 'integration':
    redis_sync_patcher.start()

def _fake_get_encrypted_redis_client(url):
    return AsyncFakeRedis()
enc_redis_patcher = patch('app.security.get_encrypted_redis_client', side_effect=_fake_get_encrypted_redis_client)
if os.environ.get('ENVIRONMENT') != 'integration':
    enc_redis_patcher.start()

# --- Mock Stripe ---
stripe_customer_patcher = patch('stripe.Customer.create', MagicMock(return_value=MagicMock(id='cus_test')))
stripe_subscription_patcher = patch('stripe.Subscription.create', MagicMock(return_value=MagicMock(id='sub_test', status='active')))
stripe_pi_patcher = patch('stripe.PaymentIntent.create', MagicMock(return_value=MagicMock(id='pi_test')))
stripe_webhook_patcher = patch(
    'stripe.Webhook.construct_event',
    side_effect=lambda payload, sig, secret: {
        'type': 'checkout.session.completed',
        'data': {
            'object': {
                'id': 'cs_test_123',
                'subscription': 'sub_test_123',
                'metadata': {'user_id': 'test_user', 'plan_id': 'pro'},
                'amount_total': 2999,
                'currency': 'usd',
                'payment_intent': 'pi_test_123'
            }
        }
    }
)
if os.environ.get('ENVIRONMENT') != 'integration':
    stripe_customer_patcher.start()
if os.environ.get('ENVIRONMENT') != 'integration':
    stripe_subscription_patcher.start()
if os.environ.get('ENVIRONMENT') != 'integration':
    stripe_pi_patcher.start()
if os.environ.get('ENVIRONMENT') != 'integration':
    stripe_webhook_patcher.start()

class _MockStripeError(Exception):
    pass
stripe_error_patcher = patch('stripe.error.StripeError', _MockStripeError)
if os.environ.get('ENVIRONMENT') != 'integration':
    stripe_error_patcher.start()

stripe_sub_modify_patcher = patch('stripe.Subscription.modify', MagicMock(return_value=MagicMock(id='sub_test')))
if os.environ.get('ENVIRONMENT') != 'integration':
    stripe_sub_modify_patcher.start()

# --- Mock OpenAI ---
class _MockChatCompletion:
    @staticmethod
    async def create(*args, **kwargs):
        class _Msg:
            content = "Mock AI response"
        class _Choice:
            message = _Msg()
        class _Resp:
            choices = [_Choice()]
            usage = {"total_tokens": kwargs.get('max_tokens', 10)}
        return _Resp()

class _MockOpenAI:
    def __init__(self, *args, **kwargs):
        self.chat = _MockChatCompletion()

openai_patcher = patch('openai.OpenAI', side_effect=_MockOpenAI)
if os.environ.get('ENVIRONMENT') != 'integration':
    openai_patcher.start()

# --- Mock InsightFace & ONNX ---
import sys
from unittest.mock import MagicMock
# Create mock insightface module
mock_insightface = MagicMock()
mock_insightface.app.FaceAnalysis = MagicMock()
sys.modules['insightface'] = mock_insightface
sys.modules['insightface.app'] = mock_insightface.app
insightface_patcher = patch('insightface.app.FaceAnalysis', MagicMock())
if os.environ.get('ENVIRONMENT') != 'integration':
    insightface_patcher.start()
onnx_patcher = patch('onnxruntime.InferenceSession', MagicMock())
if os.environ.get('ENVIRONMENT') != 'integration':
    onnx_patcher.start()

# --- Mock GeoIP ---
class _MockGeoIP2Reader:
    def __init__(self, *args, **kwargs):
        pass
    def city(self, ip):
        class Country:
            iso_code = 'US'
            name = 'United States'
        class City:
            name = 'San Francisco'
        class Location:
            latitude = 37.7749
            longitude = -122.4194
        class Subdivision:
            name = 'California'
            iso_code = 'CA'
        return MagicMock(
            country=Country(),
            city=City(),
            location=Location(),
            subdivisions=[MagicMock(most_specific=Subdivision())]
        )
geoip_patcher = patch('geoip2.database.Reader', _MockGeoIP2Reader)
if os.environ.get('ENVIRONMENT') != 'integration':
    geoip_patcher.start()

# --- Mock OAuth HTTP calls ---
class _MockHTTPXClient:
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass
    async def post(self, url, *args, **kwargs):
        class _Resp:
            def __init__(self, url):
                if 'google' in url:
                    self.status_code = 200
                    self._json = {"access_token":"mock_google","id_token":"mock_id","expires_in":3600}
                else:
                    self.status_code = 200
                    self._json = {"access_token":"mock_azure","id_token":"mock_id","expires_in":3600}
            def json(self):
                return self._json
        return _Resp(url)
    async def send(self, *args, **kwargs):
        class _Resp:
            status_code = 200
            def json(self):
                return {"access_token":"mock","id_token":"mock_id","expires_in":3600}
        return _Resp()
httpx_patcher = patch('httpx.AsyncClient', _MockHTTPXClient)
if os.environ.get('ENVIRONMENT') != 'integration':
    httpx_patcher.start()

# --- Mock boto3 (AWS SDK) ---
boto3_patcher = patch('boto3.client', MagicMock())
if os.environ.get('ENVIRONMENT') != 'integration':
    boto3_patcher.start()

# --- Mock PyTorch CUDA (force CPU) ---
torch_cuda_patcher = patch('torch.cuda.is_available', return_value=False)
if os.environ.get('ENVIRONMENT') != 'integration':
    torch_cuda_patcher.start()
torch_device_count_patcher = patch('torch.cuda.device_count', return_value=0)
if os.environ.get('ENVIRONMENT') != 'integration':
    torch_device_count_patcher.start()

# --- Mock SpeechBrain (voice) ---
import sys
from unittest.mock import MagicMock
sys.modules['speechbrain'] = MagicMock()
sys.modules['speechbrain.inference'] = MagicMock()
sys.modules['speechbrain.inference.speaker'] = MagicMock()
sys.modules['speechbrain.inference.speaker'].EncoderClassifier = MagicMock()
speechbrain_patcher = patch('speechbrain.inference.speaker.EncoderClassifier', MagicMock())
if os.environ.get('ENVIRONMENT') != 'integration':
    speechbrain_patcher.start()

# --- Mock PubSub and WebSocket initialization during app startup ---
pubsub_init_patcher = patch('app.pubsub.pubsub_manager.initialize', new_callable=AsyncMock)
if os.environ.get('ENVIRONMENT') != 'integration':
    pubsub_init_patcher.start()
conn_mgr_init_patcher = patch('app.websocket_manager.connection_manager.initialize', new_callable=AsyncMock)
if os.environ.get('ENVIRONMENT') != 'integration':
    conn_mgr_init_patcher.start()


# =============================================================================
# Session cleanup
# =============================================================================
def pytest_sessionfinish(session, exitstatus):
    """Stop all patches at the end of the test session."""
    patches = [
        get_db_patcher, init_db_patcher,
        redis_async_patcher, redis_sync_patcher, enc_redis_patcher,
        stripe_customer_patcher, stripe_subscription_patcher, stripe_pi_patcher,
        stripe_webhook_patcher, stripe_error_patcher, stripe_sub_modify_patcher,
        openai_patcher, insightface_patcher, onnx_patcher,
        geoip_patcher, httpx_patcher, boto3_patcher,
        torch_cuda_patcher, torch_device_count_patcher, speechbrain_patcher,
        pubsub_init_patcher, conn_mgr_init_patcher
    ]
    for p in patches:
        try:
            p.stop()
        except Exception:
            pass

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope='session')
def event_loop():
    """Create a session‑scoped event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def client():
    """FastAPI TestClient (imports app after all patches are in place)."""
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_db():
    """Provide the global in‑memory DB and reset it before each test."""
    _mock_db.reset()
    return _mock_db

@pytest.fixture(autouse=True)
def reset_mock_db():
    """Automatically reset the global mock DB before every test to ensure isolation."""
    _mock_db.reset()

@pytest.fixture
def mock_jwt_token():
    """Generate a valid JWT for testing."""
    import jwt
    from datetime import datetime, timedelta
    payload = {
        'user_id': 'test_user',
        'role': 'viewer',
        'org_id': 'test_org',
        'permissions': ['ENROLL_IDENTITY', 'VIEW_RECOGNITIONS'],
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=1),
        'jti': str(uuid.uuid4())
    }
    secret = os.environ.get('JWT_SECRET', 'test-jwt-secret-key-64byte-long-string-here-for-HS256')
    return jwt.encode(payload, secret, algorithm='HS256')

@pytest.fixture
def authenticated_client(client, mock_jwt_token):
    """Client with Authorization header set."""
    client.headers['Authorization'] = f'Bearer {mock_jwt_token}'
    yield client
    client.headers.pop('Authorization', None)

@pytest.fixture
def bypass_auth():
    """Add endpoints to PUBLIC_PATHS to bypass authentication for tests."""
    from app.middleware.authentication import PUBLIC_PATHS
    PUBLIC_PATHS.update({
        '/api/subscriptions',
        '/api/payments/create-session',
        '/api/payments/history',
        '/api/payments/invoice',
        '/api/usage/current',
        '/api/usage/limits',
        '/api/users',
        '/api/plans',
        '/api/webhooks',
        '/api/ai_assistant',
        '/api/support/tickets',
        '/api/webhooks/stripe',
        '/api/oauth/login/azure_ad',
        '/api/oauth/login/google',
        '/health', '/api/health'
    })
    yield
    # Do not remove to avoid affecting other tests
