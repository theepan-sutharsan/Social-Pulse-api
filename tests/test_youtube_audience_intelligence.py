"""Focused tests for audience-intelligence parsing and evidence aggregation."""
import json
import os
from datetime import datetime

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "audience-test-secret")

from app import create_app
from app.extensions import db
from app.services.audience_intelligence_service import build_report, classify_comment
from app.services.youtube_audience_service import AudienceYouTubeError, estimate_usage, parse_video_id


@pytest.fixture()
def app():
    from app.config import Config

    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        JWT_SECRET_KEY = "audience-test-secret-key"
        YOUTUBE_API_KEY = ""

    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def test_video_id_parser_supports_watch_short_and_shorts_urls():
    assert parse_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10") == "dQw4w9WgXcQ"
    assert parse_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert parse_video_id("https://youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    with pytest.raises(AudienceYouTubeError):
        parse_video_id("https://example.com/not-youtube")


def test_usage_estimate_is_explicitly_labeled(app):
    with app.app_context():
        usage = estimate_usage(5000)
    assert usage["estimated_api_pages"] == 50
    assert usage["estimated_ai_batches"] > 0
    assert usage["label"].startswith("Estimated")


def test_report_contains_evidence_backed_metrics():
    comments = [
        {"comment_id": "a", "text": "Amazing tutorial, please make part 2!", "likes": 4, "replies": 1, "published_at": "2026-08-09T10:00:00+00:00"},
        {"comment_id": "b", "text": "The audio is unclear and confusing?", "likes": 1, "replies": 0, "published_at": "2026-08-10T10:00:00+00:00"},
    ]
    analyses = [classify_comment(comment, set()) for comment in comments]
    report = build_report({"external_id": "dQw4w9WgXcQ", "title": "Test", "views": 10000, "published_at": datetime(2026, 8, 9, 9, 0, 0)}, comments, analyses)
    assert 0 <= report["audience_score"] <= 100
    assert report["kpis"]["positive_percentage"] + report["kpis"]["negative_percentage"] + report["kpis"]["mixed_percentage"] + report["kpis"]["neutral_percentage"] == 100
    assert report["questions"]
    assert report["content_opportunities"]
    assert report["analysis_metadata"]["deterministic_metrics"] is True
    json.dumps(report)


def test_estimate_route_requires_authentication(client):
    response = client.post("/api/youtube-audience/estimate", json={"video_url": "https://youtu.be/dQw4w9WgXcQ", "requested_count": 100})
    assert response.status_code == 401


def test_comment_fetch_follows_reply_pages(app, monkeypatch):
    from app.services import youtube_audience_service

    def fake_request(endpoint, params):
        if endpoint == "commentThreads":
            return {
                "items": [{
                    "id": "thread-1",
                    "snippet": {"totalReplyCount": 2, "topLevelComment": {"id": "top-1", "snippet": {"textOriginal": "Top comment"}}},
                    "replies": {"comments": [{"id": "reply-1", "snippet": {"textOriginal": "First reply"}}]},
                }],
            }
        return {"items": [{"id": "reply-2", "snippet": {"textOriginal": "Second reply"}}]}

    monkeypatch.setattr(youtube_audience_service, "_request", fake_request)
    with app.app_context():
        result = youtube_audience_service.fetch_comments("dQw4w9WgXcQ", 3)
    assert [row["comment_id"] for row in result["comments"]] == ["top-1", "reply-1", "reply-2"]
