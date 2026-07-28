"""
Social Pulse API — Account Tests
"""
import pytest
import os
os.environ.setdefault("DB_NAME", "social_pulse_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("FLASK_DEBUG", "0")
os.environ.setdefault("YOUTUBE_API_KEY", "")

from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    from app.config import Config
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        JWT_SECRET_KEY = "test-secret-key"
        YOUTUBE_API_KEY = ""

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
    yield
    with app.app_context():
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


def _register_and_login(client, email="member@test.com", role="member"):
    client.post("/api/auth/register", json={
        "email": email, "password": "pass1234", "full_name": "Test User"
    })
    resp = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
    return resp.get_json()["access_token"]


def test_get_accounts_empty(client):
    token = _register_and_login(client)
    resp = client.get("/api/accounts", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["accounts"] == []


def test_connect_youtube_stub(client):
    token = _register_and_login(client)
    resp = client.post(
        "/api/accounts/youtube",
        json={"channel_id": "UCtest12345"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # With stub YouTube (no API key), should succeed
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["account"]["platform"] == "youtube"
    assert data["account"]["platform_account_id"] == "UCtest12345"


def test_connect_youtube_missing_channel_id(client):
    token = _register_and_login(client)
    resp = client.post(
        "/api/accounts/youtube",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "errors" in resp.get_json()


def test_connect_youtube_duplicate(client):
    token = _register_and_login(client)
    client.post(
        "/api/accounts/youtube",
        json={"channel_id": "UCduplicate"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = client.post(
        "/api/accounts/youtube",
        json={"channel_id": "UCduplicate"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_get_instagram_oauth_url(client):
    token = _register_and_login(client)
    resp = client.get(
        "/api/accounts/instagram/oauth-url",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "oauth_url" in resp.get_json()


def test_delete_account(client):
    token = _register_and_login(client)
    create_resp = client.post(
        "/api/accounts/youtube",
        json={"channel_id": "UCdeleteme"},
        headers={"Authorization": f"Bearer {token}"},
    )
    account_id = create_resp.get_json()["account"]["id"]
    del_resp = client.delete(
        f"/api/accounts/{account_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 200


def test_sync_account_stub(client):
    token = _register_and_login(client)
    create_resp = client.post(
        "/api/accounts/youtube",
        json={"channel_id": "UCsync123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    account_id = create_resp.get_json()["account"]["id"]
    sync_resp = client.post(
        f"/api/accounts/{account_id}/sync",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sync_resp.status_code == 200
    data = sync_resp.get_json()
    assert "videos_fetched" in data
