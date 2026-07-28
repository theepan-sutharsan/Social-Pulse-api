"""
Social Pulse API — Dashboard Tests
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


def _register_and_login(client, email="dash@test.com"):
    client.post("/api/auth/register", json={
        "email": email, "password": "pass1234", "full_name": "Dash User"
    })
    resp = client.post("/api/auth/login", json={"email": email, "password": "pass1234"})
    return resp.get_json()["access_token"]


def test_get_dashboard_empty(client):
    token = _register_and_login(client)
    resp = client.get("/api/me/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "accounts" in data
    assert "recent_videos" in data
    assert "growth_series" in data
    assert "recent_suggestions" in data
    assert "totals" in data


def test_dashboard_pdf_export(client):
    token = _register_and_login(client)
    resp = client.get("/api/me/dashboard/pdf", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.content_type == "application/pdf"


def test_dashboard_requires_auth(client):
    resp = client.get("/api/me/dashboard")
    assert resp.status_code == 401
