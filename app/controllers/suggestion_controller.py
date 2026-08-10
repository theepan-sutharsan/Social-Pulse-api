"""
Social Pulse API — Suggestion Controller
AI suggestion generation, retrieval, export, and PDF report.
"""
from flask import jsonify, request
from flask_jwt_extended import get_current_user
from app.extensions import db
from app.models.suggestion_model import Suggestion
from app.models.suggestion_source_model import SuggestionSource
from app.models.video_model import Video
from app.models.video_metric_model import VideoMetric
from app.models.connected_account_model import ConnectedAccount
from app.models.tracked_channel_model import TrackedChannel
from app.utils import utc_now
from app.utils.csv_utils import rows_to_csv_response
from app.utils.pdf_utils import document_pdf_response, table_pdf_response
from app.integrations import ai_client
from datetime import date
import json

VALID_TYPES = ["title", "caption", "hook", "hashtag", "thumbnail_concept", "posting_time", "content_calendar"]


def _validate_suggestion_payload(data: dict) -> list:
    errors = []
    if not data.get("type") or data["type"] not in VALID_TYPES:
        errors.append(f"type must be one of: {', '.join(VALID_TYPES)}")
    if not data.get("connected_account_id") and not data.get("tracked_channel_id"):
        errors.append("Either connected_account_id or tracked_channel_id is required.")
    if data.get("connected_account_id") and data.get("tracked_channel_id"):
        errors.append("Provide only one of connected_account_id or tracked_channel_id.")
    return errors


def generate_suggestion():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    errors = _validate_suggestion_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    connected_account_id = data.get("connected_account_id")
    tracked_channel_id = data.get("tracked_channel_id")
    suggestion_type = data["type"]
    account_name = ""

    # Verify ownership & gather videos
    if connected_account_id:
        account = ConnectedAccount.query.get(connected_account_id)
        if not account:
            return jsonify({"error": "Connected account not found."}), 404
        if user.role != "admin" and account.user_id != user.id:
            return jsonify({"error": "Forbidden."}), 403
        account_name = account.display_name
        videos_q = Video.query.filter_by(connected_account_id=connected_account_id)
    else:
        channel = TrackedChannel.query.get(tracked_channel_id)
        if not channel:
            return jsonify({"error": "Tracked channel not found."}), 404
        account_name = channel.channel_name
        videos_q = Video.query.filter_by(tracked_channel_id=tracked_channel_id)

    videos_raw = videos_q.order_by(Video.fetched_at.desc()).limit(50).all()

    # Enrich with latest metrics
    video_dicts = []
    for v in videos_raw:
        vd = v.to_dict()
        latest_m = (
            VideoMetric.query.filter_by(video_id=v.id)
            .order_by(VideoMetric.recorded_at.desc())
            .first()
        )
        if latest_m:
            vd.update({"views": latest_m.views, "likes": latest_m.likes,
                        "comments": latest_m.comments, "shares": latest_m.shares})
        video_dicts.append(vd)

    # API-only override retained for integrations and offline tests. The frontend
    # intentionally sends no provider, so normal requests use Gemini-first auto routing.
    provider = data.get("provider")

    # Call AI
    try:
        output = ai_client.generate_suggestion(
            suggestion_type, video_dicts, account_name, provider=provider
        )
    except ai_client.AIProviderError as e:
        return jsonify({"error": str(e)}), 400

    # Build input context summary
    input_context = f"Account: {account_name} | Type: {suggestion_type} | Videos analyzed: {len(video_dicts)}"

    suggestion = Suggestion(
        user_id=user.id,
        connected_account_id=connected_account_id,
        tracked_channel_id=tracked_channel_id,
        type=suggestion_type,
        input_context=input_context,
        output=output,
        created_at=utc_now(),
    )
    try:
        db.session.add(suggestion)
        db.session.flush()

        # Link source videos (many-to-many — SIGNATURE)
        for v in videos_raw[:10]:
            source = SuggestionSource(
                suggestion_id=suggestion.id,
                video_id=v.id,
                created_at=utc_now(),
            )
            db.session.add(source)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to save suggestion: {str(e)}"}), 500

    return jsonify({"message": "Suggestion generated.", "suggestion": suggestion.to_dict()}), 201


def get_suggestions():
    user = get_current_user()
    if user.role == "admin":
        suggestions = Suggestion.query.order_by(Suggestion.created_at.desc()).all()
    else:
        suggestions = Suggestion.query.filter_by(user_id=user.id).order_by(Suggestion.created_at.desc()).all()
    return jsonify({"suggestions": [s.to_dict() for s in suggestions]}), 200


def get_suggestion(suggestion_id: int):
    user = get_current_user()
    suggestion = Suggestion.query.get(suggestion_id)
    if not suggestion:
        return jsonify({"error": "Suggestion not found."}), 404
    if user.role != "admin" and suggestion.user_id != user.id:
        return jsonify({"error": "Forbidden."}), 403

    # Include source videos
    sources = SuggestionSource.query.filter_by(suggestion_id=suggestion_id).all()
    source_videos = []
    for src in sources:
        video = Video.query.get(src.video_id)
        if video:
            vd = video.to_dict()
            vd["source_link_id"] = src.id
            source_videos.append(vd)

    result = suggestion.to_dict()
    result["source_videos"] = source_videos
    return jsonify({"suggestion": result}), 200


def delete_suggestion(suggestion_id: int):
    user = get_current_user()
    suggestion = Suggestion.query.get(suggestion_id)
    if not suggestion:
        return jsonify({"error": "Suggestion not found."}), 404
    if user.role != "admin" and suggestion.user_id != user.id:
        return jsonify({"error": "Forbidden."}), 403
    try:
        db.session.delete(suggestion)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Delete failed: {str(e)}"}), 500
    return jsonify({"message": "Suggestion deleted."}), 200


def export_suggestion_pdf(suggestion_id: int):
    user = get_current_user()
    suggestion = Suggestion.query.get(suggestion_id)
    if not suggestion:
        return jsonify({"error": "Suggestion not found."}), 404
    if user.role != "admin" and suggestion.user_id != user.id:
        return jsonify({"error": "Forbidden."}), 403

    sources = SuggestionSource.query.filter_by(suggestion_id=suggestion_id).all()
    source_titles = []
    for src in sources:
        v = Video.query.get(src.video_id)
        if v:
            source_titles.append(v.title or f"Video #{v.id}")

    # Determine account name
    target = "—"
    if suggestion.connected_account_id:
        acc = ConnectedAccount.query.get(suggestion.connected_account_id)
        target = f"{acc.display_name} ({acc.platform})" if acc else "Unknown"
    elif suggestion.tracked_channel_id:
        ch = TrackedChannel.query.get(suggestion.tracked_channel_id)
        target = f"{ch.channel_name} (tracked)" if ch else "Unknown"

    output_text = json.dumps(suggestion.output, indent=2) if suggestion.output else "N/A"

    sections = [
        {
            "heading": "Suggestion Details",
            "fields": [
                ("Suggestion ID", suggestion.id),
                ("Type", suggestion.type),
                ("Target", target),
                ("Generated At", suggestion.created_at.isoformat() if suggestion.created_at else ""),
                ("Input Context", suggestion.input_context or ""),
            ],
        },
        {
            "heading": "Source Videos (Many-to-Many)",
            "body": "\n".join(f"• {t}" for t in source_titles) or "No source videos.",
        },
        {
            "heading": "Generated Output",
            "body": output_text,
        },
    ]

    filename = f"suggestion-{suggestion_id}-{date.today().isoformat()}.pdf"
    return document_pdf_response(filename, f"Social Pulse — {suggestion.type.title()} Suggestion Report", sections)


def export_suggestions_csv():
    user = get_current_user()
    if user.role == "admin":
        suggestions = Suggestion.query.all()
    else:
        suggestions = Suggestion.query.filter_by(user_id=user.id).all()

    headers = ["type", "target", "output_summary", "created_at"]
    rows = []
    for s in suggestions:
        if s.connected_account_id:
            acc = ConnectedAccount.query.get(s.connected_account_id)
            target = f"{acc.display_name} ({acc.platform} - own account)" if acc else "Unknown"
        elif s.tracked_channel_id:
            ch = TrackedChannel.query.get(s.tracked_channel_id)
            target = f"{ch.channel_name} ({ch.platform} - tracked)" if ch else "Unknown"
        else:
            target = "—"

        output = s.output or {}
        # Build a brief summary
        if isinstance(output, dict):
            keys = list(output.keys())
            first_val = output.get(keys[0], "") if keys else ""
            if isinstance(first_val, list):
                summary = f"{len(first_val)} {keys[0]} generated"
            else:
                summary = str(first_val)[:80]
        else:
            summary = str(output)[:80]

        rows.append([
            s.type, target, summary,
            s.created_at.isoformat() if s.created_at else "",
        ])

    filename = f"suggestions-{date.today().isoformat()}.csv"
    return rows_to_csv_response(filename, headers, rows)
