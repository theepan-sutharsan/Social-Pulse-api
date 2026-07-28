"""
Social Pulse API — Video Tests
"""
import pytest
import os
os.environ.setdefault("DB_NAME", "social_pulse_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("FLASK_DEBUG", "0")

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


def _setup_member_with_videos(client):
    client.post("/api/auth/register", json={
        "email": "vid@test.com", "password": "pass1234", "full_name": "Vid User"
    })
    login_resp = client.post("/api/auth/login", json={"email": "vid@test.com", "password": "pass1234"})
    token = login_resp.get_json()["access_token"]

    create_resp = client.post(
        "/api/accounts/youtube",
        json={"channel_id": "UCvidtest"},
        headers={"Authorization": f"Bearer {token}"},
    )
    account_id = create_resp.get_json()["account"]["id"]
    client.post(f"/api/accounts/{account_id}/sync", headers={"Authorization": f"Bearer {token}"})
    return token, account_id


def test_get_videos_for_account(client):
    token, account_id = _setup_member_with_videos(client)
    resp = client.get(
        f"/api/videos?account_id={account_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "videos" in data
    assert len(data["videos"]) > 0


def test_get_video_detail(client):
    token, account_id = _setup_member_with_videos(client)
    videos_resp = client.get(
        f"/api/videos?account_id={account_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    video_id = videos_resp.get_json()["videos"][0]["id"]
    resp = client.get(f"/api/videos/{video_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "video" in resp.get_json()


def test_get_video_metrics(client):
    token, account_id = _setup_member_with_videos(client)
    videos_resp = client.get(
        f"/api/videos?account_id={account_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    video_id = videos_resp.get_json()["videos"][0]["id"]
    resp = client.get(f"/api/videos/{video_id}/metrics", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "metrics" in resp.get_json()


def test_export_videos_csv(client):
    token, account_id = _setup_member_with_videos(client)
    resp = client.get("/api/videos/export", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "text/csv" in resp.content_type


def test_export_videos_pdf(client):
    token, account_id = _setup_member_with_videos(client)
    resp = client.get("/api/videos/export?format=pdf", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.content_type == "application/pdf"
