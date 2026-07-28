"""
Social Pulse API — Tracked Channel Tests
"""
import pytest
import os
os.environ.setdefault("DB_NAME", "social_pulse_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("FLASK_DEBUG", "0")

from app import create_app
from app.extensions import db as _db
import io


@pytest.fixture(scope="session")
def app():
    from app.config import Config
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        JWT_SECRET_KEY = "test-secret-key"

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


def _register_admin(client):
    client.post("/api/auth/register", json={
        "email": "admin@test.com", "password": "admin123", "full_name": "Admin", "role": "admin"
    })
    resp = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "admin123"})
    return resp.get_json()["access_token"]


def _register_member(client):
    client.post("/api/auth/register", json={
        "email": "member@test.com", "password": "pass1234", "full_name": "Member"
    })
    resp = client.post("/api/auth/login", json={"email": "member@test.com", "password": "pass1234"})
    return resp.get_json()["access_token"]


def test_member_can_list_tracked_channels(client):
    token = _register_member(client)
    resp = client.get("/api/tracked-channels", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_member_cannot_create_tracked_channel(client):
    token = _register_member(client)
    resp = client.post(
        "/api/tracked-channels",
        json={"channel_id": "UCtest", "channel_name": "Test Channel", "niche": "Tech"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_admin_can_create_tracked_channel(client):
    token = _register_admin(client)
    resp = client.post(
        "/api/tracked-channels",
        json={"channel_id": "UCadmintest", "channel_name": "Admin Test Channel", "niche": "Tech"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["tracked_channel"]["channel_id"] == "UCadmintest"


def test_admin_can_delete_tracked_channel(client):
    token = _register_admin(client)
    create_resp = client.post(
        "/api/tracked-channels",
        json={"channel_id": "UCdeleteme", "channel_name": "Delete Me", "niche": "Tech"},
        headers={"Authorization": f"Bearer {token}"},
    )
    ch_id = create_resp.get_json()["tracked_channel"]["id"]
    del_resp = client.delete(f"/api/tracked-channels/{ch_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_resp.status_code == 200


def test_admin_csv_import(client):
    token = _register_admin(client)
    csv_content = b"channel_id,channel_name,niche\nUCimport1,Import Channel 1,Technology\nUCimport2,Import Channel 2,Music\n"
    data = {"file": (io.BytesIO(csv_content), "channels.csv")}
    resp = client.post(
        "/api/tracked-channels/import",
        data=data,
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    result = resp.get_json()
    assert result["created"] == 2
    assert result["skipped"] == 0


def test_admin_csv_export(client):
    token = _register_admin(client)
    client.post(
        "/api/tracked-channels",
        json={"channel_id": "UCexport1", "channel_name": "Export Channel", "niche": "Gaming"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = client.get("/api/tracked-channels/export", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "text/csv" in resp.content_type
