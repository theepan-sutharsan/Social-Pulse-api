"""Focused tests for audience-intelligence parsing and evidence aggregation."""
import json
import os
from datetime import datetime

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "audience-test-secret")

from app import create_app
from app.extensions import db
from app.models.user_model import User
from app.models.video_model import Video
from app.models.youtube_audience_model import AudienceAnalysisRun
from app.services.audience_intelligence_service import build_report, classify_comment
from app.services.audience_ai_service import _validate_batch
from app.services import audience_job_service
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


def test_ai_batch_defaults_optional_fields_used_by_worker():
    result = _validate_batch({
        "comments": [{
            "comment_id": "comment-1",
            "language": "en",
            "sentiment": "Positive",
            "emotion": "Joy",
            "topic": "Tutorial",
            "intent": "Feedback",
            "persona": "Learner",
            "cluster": "Tutorial Â· Feedback",
            "spam": False,
            "toxic": False,
            "sarcastic": False,
            "quality_score": 80,
            "confidence": 0.8,
            # Provider responses sometimes omit toxicity_severity, bot_signal,
            # and evidence even though the prompt includes them.
        }],
    }, {"comment-1"})
    assert result["comment-1"]["toxicity_severity"] is None
    assert result["comment-1"]["bot_signal"] == "Likely Organic"
    assert result["comment-1"]["evidence"] == {}


def test_worker_completes_when_provider_omits_optional_fields(app, monkeypatch):
    with app.app_context():
        user = User(email="worker@test.com", password="password", full_name="Worker")
        db.session.add(user)
        db.session.flush()
        video = Video(platform="youtube", external_id="dQw4w9WgXcQ")
        db.session.add(video)
        db.session.flush()
        run = AudienceAnalysisRun(
            user_id=user.id,
            video_fk_id=video.id,
            external_video_id=video.external_id,
            video_url="https://youtu.be/dQw4w9WgXcQ",
            requested_count=1,
            requested_all=False,
            status="PENDING",
            configuration_json={"provider": "gemini"},
        )
        db.session.add(run)
        db.session.commit()

        monkeypatch.setattr(audience_job_service, "fetch_video_metadata", lambda _video_id: {
            "external_id": "dQw4w9WgXcQ",
            "title": "Test video",
            "description": "",
            "thumbnail_url": "",
            "channel_name": "Test channel",
            "channel_id": "UC_test",
            "published_at": datetime(2026, 8, 10, 10, 0),
            "duration": "PT1M",
            "views": 1000,
            "likes": 20,
            "comments": 1,
        })
        monkeypatch.setattr(audience_job_service, "fetch_comments", lambda *_args: {
            "comments": [{
                "comment_id": "comment-1",
                "parent_comment_id": None,
                "author_name": "Viewer",
                "author_channel_id": None,
                "text": "Great video!",
                "likes": 2,
                "replies": 0,
                "published_at": datetime(2026, 8, 10, 10, 0),
                "updated_at": datetime(2026, 8, 10, 10, 0),
            }],
            "pages": 1,
        })
        # Simulate a valid provider row that omits fields the worker treats as
        # optional in real Gemini/Claude responses.
        monkeypatch.setattr(audience_job_service, "classify_batch_with_ai", lambda *_args: ({
            "comment-1": {
                "comment_id": "comment-1",
                "language": "en",
                "sentiment": "Positive",
                "emotion": "Joy",
                "topic": "Tutorial",
                "intent": "Feedback",
                "persona": "Learner",
                "cluster": "Tutorial - Feedback",
                "spam": False,
                "toxic": False,
                "sarcastic": False,
                "quality_score": 80,
                "confidence": 0.8,
                "evidence": {},
            },
        }, "gemini"))
        monkeypatch.setattr(audience_job_service, "enrich_report", lambda report, *_args: (report, "deterministic"))

        audience_job_service._run_analysis(app, run.id)
        db.session.expire_all()
        saved = AudienceAnalysisRun.query.get(run.id)
        assert saved.status == "COMPLETED", saved.error_message
        assert saved.error_message is None


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
