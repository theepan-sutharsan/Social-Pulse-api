"""
Social Pulse API — Video Controller
Handles video listing, detail, metrics, and export.
"""
from flask import jsonify, request
from flask_jwt_extended import get_current_user
from app.extensions import db
from app.models.video_model import Video
from app.models.video_metric_model import VideoMetric
from app.models.connected_account_model import ConnectedAccount
from app.utils.csv_utils import rows_to_csv_response
from app.utils.pdf_utils import table_pdf_response
from datetime import date


def get_videos():
    user = get_current_user()
    account_id = request.args.get("account_id", type=int)
    tracked_channel_id = request.args.get("tracked_channel_id", type=int)
    platform = request.args.get("platform")

    query = Video.query
    if user.role != "admin":
        # Member: own account videos + tracked channel videos
        owned_account_ids = [
            a.id for a in ConnectedAccount.query.filter_by(user_id=user.id).all()
        ]
        query = query.filter(
            db.or_(
                Video.connected_account_id.in_(owned_account_ids),
                Video.tracked_channel_id.isnot(None),
            )
        )
    if account_id:
        query = query.filter_by(connected_account_id=account_id)
    if tracked_channel_id:
        query = query.filter_by(tracked_channel_id=tracked_channel_id)
    if platform:
        query = query.filter_by(platform=platform)

    videos = query.order_by(Video.published_at.desc()).all()
    return jsonify({"videos": [v.to_dict() for v in videos]}), 200


def get_video(video_id: int):
    user = get_current_user()
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found."}), 404
    if user.role != "admin":
        owned_ids = [a.id for a in ConnectedAccount.query.filter_by(user_id=user.id).all()]
        if video.connected_account_id and video.connected_account_id not in owned_ids:
            return jsonify({"error": "Forbidden."}), 403
    return jsonify({"video": video.to_dict()}), 200


def get_video_metrics(video_id: int):
    user = get_current_user()
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found."}), 404
    if user.role != "admin":
        owned_ids = [a.id for a in ConnectedAccount.query.filter_by(user_id=user.id).all()]
        if video.connected_account_id and video.connected_account_id not in owned_ids:
            return jsonify({"error": "Forbidden."}), 403

    metrics = VideoMetric.query.filter_by(video_id=video_id).order_by(VideoMetric.recorded_at.asc()).all()
    return jsonify({"metrics": [m.to_dict() for m in metrics]}), 200


def export_videos(fmt: str = "csv"):
    user = get_current_user()
    if user.role == "admin":
        videos = Video.query.all()
    else:
        owned_ids = [a.id for a in ConnectedAccount.query.filter_by(user_id=user.id).all()]
        videos = Video.query.filter(Video.connected_account_id.in_(owned_ids)).all()

    headers = ["platform", "title", "views", "likes", "comments", "published_at"]
    rows = []
    for v in videos:
        latest_metric = (
            VideoMetric.query.filter_by(video_id=v.id)
            .order_by(VideoMetric.recorded_at.desc())
            .first()
        )
        rows.append([
            v.platform,
            v.title or "",
            latest_metric.views if latest_metric else 0,
            latest_metric.likes if latest_metric else 0,
            latest_metric.comments if latest_metric else 0,
            v.published_at.isoformat() if v.published_at else "",
        ])

    filename = f"videos-{date.today().isoformat()}"
    if fmt == "pdf":
        return table_pdf_response(filename + ".pdf", "Social Pulse — Video Performance Report", headers, rows)
    return rows_to_csv_response(filename + ".csv", headers, rows)
