"""
Social Pulse API — Suggestion Tests
"""
import pytest
import os
os.environ.setdefault("DB_NAME", "social_pulse_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("FLASK_DEBUG", "0")
os.environ.setdefault("ANTHROPIC_API_KEY", "")

from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    from app.config import Config
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        JWT_SECRET_KEY = "test-secret-key"
        ANTHROPIC_API_KEY = ""
        YOUTUBE_API_KEY = ""
        GEMINI_API_KEY = ""

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


def _register_and_login(client, email="member@test.com"):
    client.post("/api/auth/register", json={
        "email": email, "password": "pass1234", "full_name": "Test Member"
    })
    resp = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
    return resp.get_json()["access_token"]


def _create_account_and_sync(client, token):
    create_resp = client.post(
        "/api/accounts/youtube",
        json={"channel_id": "UCtest_suggest"},
        headers={"Authorization": f"Bearer {token}"},
    )
    account_id = create_resp.get_json()["account"]["id"]
    client.post(f"/api/accounts/{account_id}/sync", headers={"Authorization": f"Bearer {token}"})
    return account_id


def test_generate_suggestion_stub(client):
    token = _register_and_login(client)
    account_id = _create_account_and_sync(client, token)
    resp = client.post(
        "/api/suggestions",
        json={"type": "title", "provider": "stub", "connected_account_id": account_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert "suggestion" in data
    assert data["suggestion"]["type"] == "title"
    assert data["suggestion"]["output"] is not None


def test_generate_suggestion_unconfigured_error(client):
    token = _register_and_login(client)
    account_id = _create_account_and_sync(client, token)
    resp = client.post(
        "/api/suggestions",
        json={"type": "title", "provider": "gemini", "connected_account_id": account_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data
    assert "GEMINI_API_KEY" in data["error"]


def test_generate_suggestion_invalid_type(client):
    token = _register_and_login(client)
    account_id = _create_account_and_sync(client, token)
    resp = client.post(
        "/api/suggestions",
        json={"type": "invalid_type", "provider": "stub", "connected_account_id": account_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_generate_suggestion_no_target(client):
    token = _register_and_login(client)
    resp = client.post(
        "/api/suggestions",
        json={"type": "title", "provider": "stub"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_get_suggestions_empty(client):
    token = _register_and_login(client)
    resp = client.get("/api/suggestions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["suggestions"] == []


def test_get_suggestion_with_sources(client):
    """Verify the signature many-to-many: suggestion includes source_videos."""
    token = _register_and_login(client)
    account_id = _create_account_and_sync(client, token)
    gen_resp = client.post(
        "/api/suggestions",
        json={"type": "hook", "provider": "stub", "connected_account_id": account_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    suggestion_id = gen_resp.get_json()["suggestion"]["id"]
    resp = client.get(f"/api/suggestions/{suggestion_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "source_videos" in data["suggestion"]
    # Should have source videos (from sync stub data)
    assert isinstance(data["suggestion"]["source_videos"], list)


def test_delete_suggestion(client):
    token = _register_and_login(client)
    account_id = _create_account_and_sync(client, token)
    gen_resp = client.post(
        "/api/suggestions",
        json={"type": "caption", "provider": "stub", "connected_account_id": account_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    suggestion_id = gen_resp.get_json()["suggestion"]["id"]
    del_resp = client.delete(
        f"/api/suggestions/{suggestion_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 200


def test_suggestion_not_found(client):
    token = _register_and_login(client)
    resp = client.get("/api/suggestions/99999", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
