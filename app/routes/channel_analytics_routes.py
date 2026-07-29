"""
Social Pulse API — Channel Analytics Routes
Exposes GET /api/channels/<id>/* endpoints.
"""
from flask import Blueprint
from app.middleware import jwt_or_api_key_required
from app.controllers import channel_analytics_controller

bp = Blueprint("channel_analytics", __name__, url_prefix="/api/channels")


@bp.route("/<channel_id>", methods=["GET"])
@jwt_or_api_key_required
def get_channel_detail(channel_id):
    return channel_analytics_controller.get_channel_detail(channel_id)


@bp.route("/<channel_id>/history", methods=["GET"])
@jwt_or_api_key_required
def get_channel_history(channel_id):
    return channel_analytics_controller.get_channel_history(channel_id)


@bp.route("/<channel_id>/growth", methods=["GET"])
@jwt_or_api_key_required
def get_channel_growth(channel_id):
    return channel_analytics_controller.get_channel_growth(channel_id)


@bp.route("/<channel_id>/revenue", methods=["GET"])
@jwt_or_api_key_required
def get_channel_revenue(channel_id):
    return channel_analytics_controller.get_channel_revenue(channel_id)


@bp.route("/<channel_id>/predictions", methods=["GET"])
@jwt_or_api_key_required
def get_channel_predictions(channel_id):
    return channel_analytics_controller.get_channel_predictions(channel_id)


@bp.route("/<channel_id>/top-videos", methods=["GET"])
@jwt_or_api_key_required
def get_channel_top_videos(channel_id):
    return channel_analytics_controller.get_channel_top_videos(channel_id)
