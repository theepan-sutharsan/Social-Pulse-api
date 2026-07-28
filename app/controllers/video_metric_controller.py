"""
Social Pulse API — Video Metric Controller
Dedicated controller for managing video metric operations.
"""
from flask import jsonify, request
from flask_jwt_extended import get_current_user
from app.extensions import db
from app.models.video_model import Video
from app.models.video_metric_model import VideoMetric
from app.models.connected_account_model import ConnectedAccount
from app.utils import utc_now


def get_metrics_for_video(video_id: int):
    """Get all metric snapshots for a video (time series)."""
    user = get_current_user()
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found."}), 404
    if user.role != "admin":
        owned_ids = [a.id for a in ConnectedAccount.query.filter_by(user_id=user.id).all()]
        if video.connected_account_id and video.connected_account_id not in owned_ids:
            return jsonify({"error": "Forbidden."}), 403

    metrics = (
        VideoMetric.query
        .filter_by(video_id=video_id)
        .order_by(VideoMetric.recorded_at.asc())
        .all()
    )
    return jsonify({"metrics": [m.to_dict() for m in metrics]}), 200


def get_latest_metric(video_id: int):
    """Get the most recent metric snapshot for a video."""
    user = get_current_user()
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found."}), 404
    if user.role != "admin":
        owned_ids = [a.id for a in ConnectedAccount.query.filter_by(user_id=user.id).all()]
        if video.connected_account_id and video.connected_account_id not in owned_ids:
            return jsonify({"error": "Forbidden."}), 403

    metric = (
        VideoMetric.query
        .filter_by(video_id=video_id)
        .order_by(VideoMetric.recorded_at.desc())
        .first()
    )
    if not metric:
        return jsonify({"error": "No metrics found for this video."}), 404

    return jsonify({"metric": metric.to_dict()}), 200


def record_manual_metric(video_id: int):
    """Manually record a new metric snapshot for a video."""
    user = get_current_user()
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found."}), 404
    if user.role != "admin":
        owned_ids = [a.id for a in ConnectedAccount.query.filter_by(user_id=user.id).all()]
        if video.connected_account_id and video.connected_account_id not in owned_ids:
            return jsonify({"error": "Forbidden."}), 403

    data = request.get_json(silent=True) or {}
    views = int(data.get("views", 0))
    likes = int(data.get("likes", 0))
    comments = int(data.get("comments", 0))
    shares = int(data.get("shares", 0))
    engagement = round((likes + comments + shares) / max(views, 1) * 100, 4)

    metric = VideoMetric(
        video_id=video_id,
        views=views,
        likes=likes,
        comments=comments,
        shares=shares,
        engagement_rate=engagement,
        recorded_at=utc_now(),
    )
    try:
        db.session.add(metric)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to record metric: {str(e)}"}), 500

    return jsonify({"message": "Metric recorded.", "metric": metric.to_dict()}), 201
