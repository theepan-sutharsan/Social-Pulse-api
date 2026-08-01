"""
Social Pulse API — Multi-Platform Analytics Engine & Competitor Tests
"""
import pytest
import os
os.environ.setdefault("DB_NAME", "social_pulse_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("FLASK_DEBUG", "0")

from app import create_app
from app.extensions import db as _db
from app.services import revenue_engine, ai_scoring_engine, competitor_engine


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


def _register_and_login(client):
    client.post("/api/auth/register", json={
        "email": "multi_user@test.com", "password": "pass1234", "full_name": "Multi User"
    })
    resp = client.post("/api/auth/login", json={"email": "multi_user@test.com", "password": "pass1234"})
    return resp.get_json()["access_token"]


def test_multiplatform_revenue_engine():
    ig_rev = revenue_engine.calculate_multiplatform_revenue("instagram", followers=50000, avg_engagement_rate=3.5)
    assert ig_rev["platform"] == "instagram"
    assert "sponsored_post" in ig_rev

    tiktok_rev = revenue_engine.calculate_multiplatform_revenue("tiktok", followers=100000, monthly_views=500000)
    assert tiktok_rev["platform"] == "tiktok"
    assert "creator_fund_monthly" in tiktok_rev

    linkedin_rev = revenue_engine.calculate_multiplatform_revenue("linkedin", followers=20000, avg_engagement_rate=2.5)
    assert linkedin_rev["platform"] == "linkedin"
    assert "brand_influence_score" in linkedin_rev


def test_ai_scoring_engine():
    acc = {"subscribers": 25000, "total_views": 1000000, "description": "Tech Creator Channel", "profile_image": "https://img.jpg"}
    posts = [{"views": 10000, "likes": 500, "comments": 50, "title": "Great Python Post #coding", "tags": ["python"]}]
    scores = ai_scoring_engine.calculate_ai_scores(acc, posts)
    assert 0 <= scores["overall_score"] <= 100
    assert "profile_score" in scores["scores"]
    assert "brand_score" in scores["scores"]


def test_competitor_engine():
    u_acc = {"display_name": "My Channel", "subscribers": 10000, "total_views": 500000, "platform": "youtube"}
    c_acc = {"display_name": "Rival Channel", "subscribers": 25000, "total_views": 1500000, "platform": "youtube"}
    comp = competitor_engine.compare_user_vs_competitor(u_acc, [], c_acc, [])
    assert comp["gaps"]["leader"] == "Competitor"
    assert comp["gaps"]["follower_gap"] == -15000


def test_competitors_compare_route(client):
    token = _register_and_login(client)
    resp = client.post(
        "/api/competitors/compare",
        json={"user_account_id": None, "competitor_channel_id": "@TechGuruPro"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "comparison" in resp.get_json()
