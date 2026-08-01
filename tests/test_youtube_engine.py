"""
Social Pulse API — YouTube Engine & Historical Analytics Tests
"""
import pytest
import os
os.environ.setdefault("DB_NAME", "social_pulse_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("FLASK_DEBUG", "0")

from app import create_app
from app.extensions import db as _db
from app.services import growth_engine, revenue_engine, prediction_engine, viral_score_engine, seo_engine, channel_analytics_engine, historical_tracker


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
        "email": "engine_user@test.com", "password": "pass1234", "full_name": "Engine User"
    })
    resp = client.post("/api/auth/login", json={"email": "engine_user@test.com", "password": "pass1234"})
    return resp.get_json()["access_token"]


def test_growth_metrics_engine():
    records = [
        {"subscribers": 1000, "total_views": 50000, "total_videos": 10, "date": "2026-07-01"},
        {"subscribers": 1050, "total_views": 52000, "total_videos": 11, "date": "2026-07-02"},
        {"subscribers": 1120, "total_views": 55000, "total_videos": 12, "date": "2026-07-03"},
    ]
    growth = growth_engine.calculate_growth_metrics(records)
    assert growth["daily_subscriber_growth"] == 70
    assert growth["daily_view_growth"] == 3000
    assert growth["daily_video_growth"] == 1
    assert growth["growth_percentage"] > 0


def test_revenue_estimation_engine():
    rev = revenue_engine.calculate_estimated_revenue(monthly_views=100000, total_lifetime_views=500000)
    assert rev["monthly"]["min_usd"] == 200.0  # 100k / 1000 * 2
    assert rev["monthly"]["max_usd"] == 800.0  # 100k / 1000 * 8
    assert rev["daily"]["min_usd"] > 0


def test_prediction_engine():
    records = [
        {"subscribers": 1000, "total_views": 50000},
        {"subscribers": 1100, "total_views": 55000},
    ]
    sub_pred = prediction_engine.predict_subscriber_growth(records, current_subs=1100)
    assert sub_pred["predictions"]["tomorrow"]["predicted_subscribers"] >= 1100
    assert sub_pred["predictions"]["in_30_days"]["predicted_subscribers"] > 1100

    view_pred = prediction_engine.predict_view_growth(records, current_views=55000)
    assert view_pred["predictions"]["daily_views"] > 0


def test_viral_score_engine():
    video = {
        "title": "Viral Video Test",
        "published_at": "2026-07-28T10:00:00",
        "views": 50000,
        "likes": 4000,
        "comments": 500,
    }
    viral = viral_score_engine.calculate_viral_score(video)
    assert 0 <= viral["viral_score"] <= 100
    assert "viral_level" in viral
    assert viral["metrics"]["views_per_hour"] > 0


def test_seo_engine():
    video = {
        "title": "Complete Python Tutorial for Beginners 2026",
        "description": "In this Python tutorial, you will learn programming from scratch with practical coding examples and timestamps.",
        "tags": ["python", "programming", "tutorial", "coding", "developer", "learn", "course", "basics"],
        "thumbnail_url": "https://example.com/thumb.jpg",
        "category": "Education",
    }
    seo = seo_engine.analyze_video_seo(video)
    assert seo["seo_score"] > 80
    assert isinstance(seo["recommendations"], list)


def test_channel_analytics_engine():
    ch = {"subscriber_count": 10000, "total_views": 500000, "video_count": 50}
    videos = [{"views": 10000, "likes": 500, "comments": 50} for _ in range(5)]
    analytics = channel_analytics_engine.calculate_channel_analytics(ch, videos)
    assert analytics["overall_channel_score"] > 0
    assert "channel_grade" in analytics
    assert analytics["averages"]["average_views_per_video"] == 10000.0


def test_channel_analytics_routes(client):
    token = _register_and_login(client)
    resp = client.get("/api/channels/@TechGuruPro", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "channel" in data
    assert "analytics" in data


def test_channel_growth_route(client):
    token = _register_and_login(client)
    resp = client.get("/api/channels/@TechGuruPro/growth", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "growth" in resp.get_json()


def test_channel_revenue_route(client):
    token = _register_and_login(client)
    resp = client.get("/api/channels/@TechGuruPro/revenue?low_cpm=2.0&high_cpm=8.0", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "revenue_estimate" in resp.get_json()


def test_channel_predictions_route(client):
    token = _register_and_login(client)
    resp = client.get("/api/channels/@TechGuruPro/predictions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "subscriber_predictions" in resp.get_json()


def test_daily_snapshot_worker(app):
    with app.app_context():
        res = historical_tracker.run_daily_snapshot()
        assert res["status"] == "success"
