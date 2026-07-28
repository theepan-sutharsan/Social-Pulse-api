"""
Social Pulse API — Dashboard Controller
Member-specific aggregated stats.
"""
from flask import jsonify
from flask_jwt_extended import get_current_user
from app.extensions import db
from app.models.connected_account_model import ConnectedAccount
from app.models.video_model import Video
from app.models.video_metric_model import VideoMetric
from app.models.suggestion_model import Suggestion
from app.models.tracked_channel_model import TrackedChannel
from app.utils.pdf_utils import document_pdf_response
from datetime import date


def get_dashboard():
    user = get_current_user()

    accounts = ConnectedAccount.query.filter_by(user_id=user.id).all()
    account_ids = [a.id for a in accounts]

    # Recent videos
    recent_videos = (
        Video.query.filter(Video.connected_account_id.in_(account_ids))
        .order_by(Video.published_at.desc())
        .limit(10)
        .all()
    )

    # Growth series: last 10 metric snapshots per account
    growth_series = []
    for v in recent_videos[:5]:
        metrics = (
            VideoMetric.query.filter_by(video_id=v.id)
            .order_by(VideoMetric.recorded_at.asc())
            .all()
        )
        if metrics:
            growth_series.append({
                "video_id": v.id,
                "title": v.title,
                "series": [m.to_dict() for m in metrics],
            })

    # Recent suggestions
    recent_suggestions = (
        Suggestion.query.filter_by(user_id=user.id)
        .order_by(Suggestion.created_at.desc())
        .limit(5)
        .all()
    )

    tracked_channels = TrackedChannel.query.all()

    return jsonify({
        "accounts": [a.to_dict() for a in accounts],
        "recent_videos": [v.to_dict() for v in recent_videos],
        "growth_series": growth_series,
        "recent_suggestions": [s.to_dict() for s in recent_suggestions],
        "tracked_channels_count": len(tracked_channels),
        "totals": {
            "connected_accounts": len(accounts),
            "videos": Video.query.filter(Video.connected_account_id.in_(account_ids)).count(),
            "suggestions": Suggestion.query.filter_by(user_id=user.id).count(),
        },
    }), 200


def export_dashboard_pdf():
    user = get_current_user()
    accounts = ConnectedAccount.query.filter_by(user_id=user.id).all()
    account_ids = [a.id for a in accounts]
    recent_suggestions = (
        Suggestion.query.filter_by(user_id=user.id)
        .order_by(Suggestion.created_at.desc())
        .limit(5)
        .all()
    )

    sections = [
        {
            "heading": "Connected Accounts",
            "fields": [(a.display_name, f"{a.platform} | Last synced: {a.last_synced_at.isoformat() if a.last_synced_at else 'Never'}") for a in accounts]
                      or [("", "No connected accounts.")],
        },
        {
            "heading": "Growth Snapshot",
            "fields": [
                ("Total Videos", Video.query.filter(Video.connected_account_id.in_(account_ids)).count()),
                ("Total Suggestions", Suggestion.query.filter_by(user_id=user.id).count()),
            ],
        },
        {
            "heading": "Recent AI Suggestions",
            "body": "\n".join(
                f"• [{s.type}] {s.created_at.strftime('%Y-%m-%d')}"
                for s in recent_suggestions
            ) or "No suggestions yet.",
        },
    ]
    filename = f"dashboard-summary-{date.today().isoformat()}.pdf"
    return document_pdf_response(filename, f"Social Pulse — Dashboard Summary for {user.full_name}", sections)
