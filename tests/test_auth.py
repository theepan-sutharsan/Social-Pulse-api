"""
Social Pulse API — Auth Tests
"""
import pytest
import os
from urllib.parse import parse_qs, urlparse
os.environ.setdefault("DB_NAME", "social_pulse_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("FLASK_DEBUG", "0")

from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    """Create a test Flask application with in-memory SQLite."""
    from app.config import Config
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        JWT_SECRET_KEY = "test-secret-key"
        WTF_CSRF_ENABLED = False

    application = create_app(TestConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Clean all tables between tests."""
    yield
    with app.app_context():
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


def test_register_success(client):
    resp = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "full_name": "Test User",
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert "access_token" in data
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["role"] == "member"


def test_register_missing_fields(client):
    resp = client.post("/api/auth/register", json={"email": "test@example.com"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "errors" in data


def test_register_duplicate_email(client):
    client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "password": "password123",
        "full_name": "User One",
    })
    resp = client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "password": "password456",
        "full_name": "User Two",
    })
    assert resp.status_code == 400
    assert "errors" in resp.get_json()


def test_login_success(client):
    client.post("/api/auth/register", json={
        "email": "login@example.com",
        "password": "pass1234",
        "full_name": "Login User",
    })
    resp = client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "pass1234",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.get_json()


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={
        "email": "wp@example.com",
        "password": "correct",
        "full_name": "Wrong Pass",
    })
    resp = client.post("/api/auth/login", json={
        "email": "wp@example.com",
        "password": "wrong",
    })
    assert resp.status_code == 401


def test_forgot_password_and_reset(client):
    client.application.config["DEBUG"] = True
    client.post("/api/auth/register", json={
        "email": "reset@example.com",
        "password": "oldpass123",
        "full_name": "Reset User",
    })

    request_resp = client.post("/api/auth/forgot-password", json={"email": "reset@example.com"})
    assert request_resp.status_code == 200
    reset_url = request_resp.get_json()["reset_url"]
    token = parse_qs(urlparse(reset_url).query)["token"][0]

    reset_resp = client.post("/api/auth/reset-password", json={"token": token, "password": "newpass123"})
    assert reset_resp.status_code == 200
    login_resp = client.post("/api/auth/login", json={"email": "reset@example.com", "password": "newpass123"})
    assert login_resp.status_code == 200

    client.application.config["DEBUG"] = False


def test_get_profile_authenticated(client):
    reg = client.post("/api/auth/register", json={
        "email": "profile@example.com",
        "password": "pass1234",
        "full_name": "Profile User",
    })
    token = reg.get_json()["access_token"]
    resp = client.get("/api/auth/profile", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["user"]["email"] == "profile@example.com"


def test_get_profile_unauthenticated(client):
    resp = client.get("/api/auth/profile")
    assert resp.status_code == 401


def test_update_profile(client):
    reg = client.post("/api/auth/register", json={
        "email": "update@example.com",
        "password": "pass1234",
        "full_name": "Old Name",
    })
    token = reg.get_json()["access_token"]
    resp = client.put(
        "/api/auth/profile",
        json={"full_name": "New Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["user"]["full_name"] == "New Name"
