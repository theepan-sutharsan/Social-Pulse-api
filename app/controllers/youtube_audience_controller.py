"""HTTP handlers for the versioned YouTube audience-intelligence feature."""
from __future__ import annotations

import json
from datetime import datetime

from flask import current_app, jsonify, request
from flask_jwt_extended import get_current_user
from sqlalchemy import or_

from app.extensions import db
from app.models.video_model import Video
from app.models.youtube_audience_model import AudienceAnalysisRun, AudienceComment, AudienceCommentAnalysis
from app.services.audience_job_service import enqueue_analysis
from app.services.youtube_audience_service import AudienceYouTubeError, estimate_usage, normalize_requested_count, parse_video_id
from app.utils.csv_utils import rows_to_csv_response
from app.utils.pdf_utils import document_pdf_response


ACTIVE_STATUSES = {"PENDING", "FETCHING", "PREPROCESSING", "CLASSIFYING", "CLUSTERING", "ANALYZING", "AGGREGATING", "SUMMARIZING"}


def _user():
    user = get_current_user()
    return user if user and getattr(user, "is_active", True) else None


def estimate():
    user = _user()
    if not user:
        return jsonify({"error": "Unauthorized user."}), 401
    data = request.get_json(silent=True) or {}
    try:
        count, all_available = normalize_requested_count(data.get("requested_count", 500))
        video_id = parse_video_id(data.get("video_url", ""))
    except AudienceYouTubeError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"video_id": video_id, "usage": estimate_usage(count, all_available)}), 200


def start_analysis():
    user = _user()
    if not user:
        return jsonify({"error": "Unauthorized user."}), 401
    data = request.get_json(silent=True) or {}
    video_url = (data.get("video_url") or "").strip()
    provider = (data.get("provider") or "auto").strip().lower()
    if provider not in {"auto", "gemini", "claude"}:
        return jsonify({"error": "provider must be auto, gemini, or claude."}), 400
    try:
        count, all_available = normalize_requested_count(data.get("requested_count", 500))
        video_id = parse_video_id(video_url)
    except AudienceYouTubeError as exc:
        return jsonify({"error": str(exc)}), 400

    duplicate = (
        AudienceAnalysisRun.query
        .filter(
            AudienceAnalysisRun.user_id == user.id,
            AudienceAnalysisRun.external_video_id == video_id,
            AudienceAnalysisRun.status.in_(ACTIVE_STATUSES),
        )
        .order_by(AudienceAnalysisRun.created_at.desc())
        .first()
    )
    if duplicate:
        return jsonify({"message": "An analysis for this video is already running.", "run": duplicate.to_dict(include_report=False), "usage": estimate_usage(count, all_available)}), 202

    video = Video.query.filter_by(platform="youtube", external_id=video_id).first()
    if not video:
        video = Video(platform="youtube", external_id=video_id, title="Video metadata pending")
        db.session.add(video)
        db.session.flush()

    run = AudienceAnalysisRun(
        user_id=user.id,
        video_fk_id=video.id,
        external_video_id=video_id,
        video_url=video_url,
        status="PENDING",
        requested_count=count,
        requested_all=all_available,
        current_stage="PENDING",
        progress_pct=0,
        configuration_json={"provider": provider, "usage": estimate_usage(count, all_available)},
    )
    db.session.add(run)
    db.session.commit()
    enqueue_analysis(current_app._get_current_object(), run.id)
    return jsonify({
        "message": "Audience analysis queued.",
        "run": run.to_dict(include_report=False),
        "usage": estimate_usage(count, all_available),
    }), 202


def _owned_run(run_id: int):
    user = _user()
    if not user:
        return None, (jsonify({"error": "Unauthorized user."}), 401)
    run = AudienceAnalysisRun.query.get(run_id)
    if not run:
        return None, (jsonify({"error": "Audience analysis run not found."}), 404)
    if user.role != "admin" and run.user_id != user.id:
        return None, (jsonify({"error": "Forbidden. Access denied."}), 403)
    return run, None


def get_run(run_id: int):
    run, error = _owned_run(run_id)
    if error:
        return error
    return jsonify({"run": run.to_dict(include_report=True)}), 200


def get_history():
    user = _user()
    if not user:
        return jsonify({"error": "Unauthorized user."}), 401
    runs = AudienceAnalysisRun.get_by_user(user.id, limit=50)
    return jsonify({"count": len(runs), "history": [run.to_dict(include_report=False) for run in runs]}), 200


def get_comments(run_id: int):
    run, error = _owned_run(run_id)
    if error:
        return error
    args = request.args
    try:
        page = max(1, int(args.get("page", 1) or 1))
        per_page = min(100, max(1, int(args.get("per_page", 25) or 25)))
    except (TypeError, ValueError):
        return jsonify({"error": "page and per_page must be valid integers."}), 400
    query = db.session.query(AudienceComment, AudienceCommentAnalysis).join(
        AudienceCommentAnalysis,
        (AudienceCommentAnalysis.comment_id == AudienceComment.id) & (AudienceCommentAnalysis.run_id == run.id),
    ).filter(AudienceComment.video_fk_id == run.video_fk_id)
    search = (args.get("q") or "").strip()[:200]
    if search:
        pattern = f"%{search}%"
        query = query.filter(or_(AudienceComment.original_text.ilike(pattern), AudienceComment.author_name.ilike(pattern), AudienceCommentAnalysis.topic.ilike(pattern)))
    for field in ("sentiment", "emotion", "language", "topic", "intent", "persona", "cluster"):
        value = (args.get(field) or "").strip()
        if value:
            model_field = getattr(AudienceCommentAnalysis, field if field != "language" else "language")
            query = query.filter(model_field == value)
    if args.get("spam") in {"true", "false"}:
        query = query.filter(AudienceCommentAnalysis.is_spam == (args.get("spam") == "true"))
    if args.get("toxicity") in {"true", "false"}:
        query = query.filter(AudienceCommentAnalysis.is_toxic == (args.get("toxicity") == "true"))
    try:
        if args.get("min_likes") is not None:
            query = query.filter(AudienceComment.like_count >= max(0, int(args.get("min_likes"))))
        if args.get("min_replies") is not None:
            query = query.filter(AudienceComment.reply_count >= max(0, int(args.get("min_replies"))))
        if args.get("min_confidence") is not None:
            query = query.filter(AudienceCommentAnalysis.confidence >= max(0.0, min(1.0, float(args.get("min_confidence")))))
        if args.get("min_quality") is not None:
            query = query.filter(AudienceCommentAnalysis.quality_score >= max(0.0, min(100.0, float(args.get("min_quality")))))
        if args.get("max_quality") is not None:
            query = query.filter(AudienceCommentAnalysis.quality_score <= max(0.0, min(100.0, float(args.get("max_quality")))))
        if args.get("date_from"):
            query = query.filter(AudienceComment.published_at >= datetime.fromisoformat(args.get("date_from").replace("Z", "+00:00")).replace(tzinfo=None))
        if args.get("date_to"):
            query = query.filter(AudienceComment.published_at <= datetime.fromisoformat(args.get("date_to").replace("Z", "+00:00")).replace(tzinfo=None))
    except (TypeError, ValueError):
        return jsonify({"error": "Numeric and date filters must be valid values."}), 400
    sort = (args.get("sort") or "newest").lower()
    sort_map = {
        "most_liked": AudienceComment.like_count.desc(),
        "most_replied": AudienceComment.reply_count.desc(),
        "highest_quality": AudienceCommentAnalysis.quality_score.desc(),
        "lowest_quality": AudienceCommentAnalysis.quality_score.asc(),
        "oldest": AudienceComment.published_at.asc(),
        "newest": AudienceComment.published_at.desc(),
    }
    query = query.order_by(sort_map.get(sort, AudienceComment.published_at.desc()))
    total = query.count()
    rows = query.offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": total,
        "comments": [comment.to_dict(analysis) for comment, analysis in rows],
    }), 200


def export_csv(run_id: int):
    run, error = _owned_run(run_id)
    if error:
        return error
    rows = db.session.query(AudienceComment, AudienceCommentAnalysis).join(
        AudienceCommentAnalysis,
        (AudienceCommentAnalysis.comment_id == AudienceComment.id) & (AudienceCommentAnalysis.run_id == run.id),
    ).filter(AudienceComment.video_fk_id == run.video_fk_id).order_by(AudienceComment.published_at.asc()).all()
    headers = ["comment_id", "parent_comment_id", "author", "author_channel_id", "text", "published_at", "updated_at", "likes", "replies", "language", "sentiment", "emotion", "topic", "intent", "persona", "cluster", "spam", "toxicity", "sarcasm", "quality_score", "confidence"]
    values = []
    for comment, analysis in rows:
        values.append([
            comment.external_comment_id,
            comment.parent_external_comment_id,
            comment.author_name,
            comment.author_channel_id,
            comment.original_text,
            comment.published_at.isoformat() if comment.published_at else "",
            comment.updated_at.isoformat() if comment.updated_at else "",
            comment.like_count,
            comment.reply_count,
            analysis.language,
            analysis.sentiment,
            analysis.emotion,
            analysis.topic,
            analysis.intent,
            analysis.persona,
            analysis.cluster,
            analysis.is_spam,
            analysis.is_toxic,
            analysis.is_sarcastic,
            analysis.quality_score,
            analysis.confidence,
        ])
    return rows_to_csv_response(f"youtube-audience-{run.external_video_id}-{run.id}.csv", headers, values)


def export_pdf(run_id: int):
    run, error = _owned_run(run_id)
    if error:
        return error
    report = run.report_json or {}
    summary = report.get("summary", {}) if isinstance(report, dict) else {}
    sections = [
        {"heading": "Executive Summary", "body": report.get("executive_summary", "Report is still processing.")},
        {"heading": "Video Information", "fields": [("Video ID", run.external_video_id), ("Video URL", run.video_url), ("Requested", "All available" if run.requested_all else f"{run.requested_count:,}"), ("Analyzed", run.analyzed_count)]},
        {"heading": "Audience KPIs", "fields": [(str(key).replace("_", " ").title(), value) for key, value in (report.get("kpis", {}) or {}).items()]},
        {"heading": "Audience Reaction", "fields": [("Score", f"{report.get('audience_score', 0)}/100"), ("Assessment", report.get("audience_score_label", "Uncertain"))]},
        {"heading": "Sentiment & Emotions", "body": json.dumps({"sentiment": report.get("sentiment", []), "emotions": report.get("emotions", []), "languages": report.get("languages", [])}, ensure_ascii=False, indent=2)},
        {"heading": "Topics & Topic Sentiment", "body": json.dumps({"top_topics": report.get("top_topics", []), "topic_sentiment": report.get("topic_sentiment", [])}, ensure_ascii=False, indent=2)},
        {"heading": "What Viewers Said", "fields": [("Loved", summary.get("what_viewers_loved", "")), ("Main problem", summary.get("main_problem", "")), ("Want next", summary.get("what_viewers_want", "")), ("Opportunity", summary.get("biggest_opportunity", ""))]},
        {"heading": "Questions, Complaints & Pain Points", "body": json.dumps({"questions": report.get("questions", [])[:10], "complaints": report.get("complaints", [])[:10], "pain_points": report.get("pain_points", [])[:10]}, ensure_ascii=False, indent=2)},
        {"heading": "Demand & Audience Segments", "body": json.dumps({"audience_demand": report.get("audience_demand", []), "audience_intent": report.get("audience_intent", []), "audience_personas": report.get("audience_personas", [])}, ensure_ascii=False, indent=2)},
        {"heading": "Content Opportunities", "body": json.dumps(report.get("content_opportunities", []), ensure_ascii=False, indent=2)},
        {"heading": "Engagement & Safety", "body": json.dumps({"engagement": report.get("engagement", {}), "comment_quality": report.get("comment_quality", {}), "spam_analysis": report.get("spam_analysis", {}), "bot_analysis": report.get("bot_analysis", {}), "toxicity": report.get("toxicity", {}), "sarcasm": report.get("sarcasm", {})}, ensure_ascii=False, indent=2)},
        {"heading": "Priority Actions", "body": json.dumps(report.get("priority_actions", []), ensure_ascii=False, indent=2)},
        {"heading": "Business Insights & Reply Opportunities", "body": json.dumps({"business_insights": report.get("business_insights", []), "reply_opportunities": report.get("reply_opportunities", [])[:10], "creator_recommendations": report.get("creator_recommendations", [])}, ensure_ascii=False, indent=2)},
        {"heading": "Historical Comparison & Evidence", "body": json.dumps({"historical_comparison": report.get("historical_comparison", {}), "suggestions": report.get("suggestions", [])[:10], "positive_feedback": report.get("positive_feedback", [])[:10], "negative_feedback": report.get("negative_feedback", [])[:10]}, ensure_ascii=False, indent=2)},
    ]
    return document_pdf_response(f"youtube-audience-{run.external_video_id}-{run.id}.pdf", "YouTube Audience Intelligence Report", sections)


def purge_video_comments(video_id: str):
    user = _user()
    if not user:
        return jsonify({"error": "Unauthorized user."}), 401
    runs = AudienceAnalysisRun.query.filter_by(user_id=user.id, external_video_id=video_id).all()
    if not runs:
        return jsonify({"error": "No audience analysis found for this video."}), 404
    run_ids = [run.id for run in runs]
    candidate_ids = {comment_id for (comment_id,) in db.session.query(AudienceCommentAnalysis.comment_id).filter(AudienceCommentAnalysis.run_id.in_(run_ids)).distinct().all()}
    shared_ids = {comment_id for (comment_id,) in db.session.query(AudienceCommentAnalysis.comment_id).filter(AudienceCommentAnalysis.comment_id.in_(candidate_ids), ~AudienceCommentAnalysis.run_id.in_(run_ids)).distinct().all()}
    comment_ids = list(candidate_ids - shared_ids)
    AudienceCommentAnalysis.query.filter(AudienceCommentAnalysis.run_id.in_(run_ids)).delete(synchronize_session=False)
    if comment_ids:
        AudienceComment.query.filter(AudienceComment.id.in_(comment_ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"message": "Stored comments and classifications were purged.", "video_id": video_id}), 200
