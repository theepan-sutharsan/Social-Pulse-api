"""
Social Pulse API — Video Analytics Routes
Exposes GET /api/videos/<id>/* historical tracking, SEO, prediction, and viral score endpoints.
"""
from flask import Blueprint
from app.middleware import jwt_or_api_key_required
from app.controllers import video_analytics_controller

bp = Blueprint("video_analytics", __name__, url_prefix="/api/videos")


@bp.route("/<int:video_id>/history", methods=["GET"])
@jwt_or_api_key_required
def get_video_history(video_id: int):
    return video_analytics_controller.get_video_history(video_id)


@bp.route("/<int:video_id>/analytics", methods=["GET"])
@jwt_or_api_key_required
def get_video_analytics(video_id: int):
    return video_analytics_controller.get_video_analytics(video_id)


@bp.route("/<int:video_id>/seo", methods=["GET"])
@jwt_or_api_key_required
def get_video_seo(video_id: int):
    return video_analytics_controller.get_video_seo(video_id)


@bp.route("/<int:video_id>/prediction", methods=["GET"])
@jwt_or_api_key_required
def get_video_prediction(video_id: int):
    return video_analytics_controller.get_video_prediction(video_id)


@bp.route("/<int:video_id>/viral-score", methods=["GET"])
@jwt_or_api_key_required
def get_video_viral_score(video_id: int):
    return video_analytics_controller.get_video_viral_score(video_id)
