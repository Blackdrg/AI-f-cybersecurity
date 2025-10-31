import pytest
from fastapi.testclient import TestClient
from app.main import app
import json
from app.security import create_token

client = TestClient(app)

# Test data
test_user = {
    "email": "test@example.com",
    "name": "Test User",
    "subscription_tier": "free"
}

special_user = {
    "email": "daredevil0101a@gmail.com",
    "name": "Special User",
    "subscription_tier": "free"  # Should be auto-upgraded to enterprise
}

test_plan = {
    "plan_id": "premium",
    "name": "Premium Plan",
    "price": 29.99,
    "features": ["unlimited_recognitions", "ai_assistant"],
    "limits": {"recognitions": 10000, "enrollments": 1000}
}


@pytest.fixture
def auth_headers():
    token = create_token("test_user_id", "user")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers():
    token = create_token("admin_user_id", "admin")
    return {"Authorization": f"Bearer {token}"}


def test_create_user():
    response = client.post("/api/users", json=test_user, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]
    assert data["subscription_tier"] == "free"


def test_create_special_user():
    response = client.post(
        "/api/users", json=special_user, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == special_user["email"]
    assert data["subscription_tier"] == "enterprise"  # Should be auto-upgraded


def test_get_current_user(auth_headers):
    # First create user
    create_response = client.post(
        "/api/users", json=test_user, headers=auth_headers)
    user_id = create_response.json()["user_id"]

    # Mock the token to return the created user_id
    token = create_token(user_id, "user")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]


def test_create_plan(admin_headers):
    response = client.post("/api/plans", json=test_plan, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"] == test_plan["plan_id"]
    assert data["price"] == test_plan["price"]


def test_get_plans():
    response = client.get("/api/plans")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_create_subscription(auth_headers):
    # Create user first
    user_response = client.post(
        "/api/users", json=test_user, headers=auth_headers)
    user_id = user_response.json()["user_id"]

    # Create plan
    plan_response = client.post(
        "/api/plans", json=test_plan, headers=admin_headers)
    plan_id = plan_response.json()["plan_id"]

    subscription_data = {"plan_id": plan_id}

    # Mock token for the created user
    token = create_token(user_id, "user")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/subscriptions",
                           json=subscription_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert data["plan_id"] == plan_id


def test_create_payment(auth_headers):
    # Create user first
    user_response = client.post(
        "/api/users", json=test_user, headers=auth_headers)
    user_id = user_response.json()["user_id"]

    payment_data = {
        "plan_id": "premium",
        "amount": 29.99
    }

    # Mock token for the created user
    token = create_token(user_id, "user")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/payments", json=payment_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert data["amount"] == 29.99


def test_get_usage(auth_headers):
    # Create user first
    user_response = client.post(
        "/api/users", json=test_user, headers=auth_headers)
    user_id = user_response.json()["user_id"]

    # Mock token for the created user
    token = create_token(user_id, "user")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/usage", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "recognitions_used" in data
    assert "enrollments_used" in data


def test_ai_assistant(auth_headers):
    query_data = {"query": "What are the premium features?"}

    response = client.post("/api/ai_assistant",
                           json=query_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "model_used" in data


def test_create_support_ticket(auth_headers):
    # Create user first
    user_response = client.post(
        "/api/users", json=test_user, headers=auth_headers)
    user_id = user_response.json()["user_id"]

    ticket_data = {
        "subject": "Test Issue",
        "description": "This is a test support ticket",
        "priority": "medium"
    }

    # Mock token for the created user
    token = create_token(user_id, "user")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/support", json=ticket_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert data["subject"] == ticket_data["subject"]


def test_get_support_tickets(auth_headers):
    # Create user first
    user_response = client.post(
        "/api/users", json=test_user, headers=auth_headers)
    user_id = user_response.json()["user_id"]

    # Mock token for the created user
    token = create_token(user_id, "user")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/support", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
