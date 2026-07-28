"""
Social Pulse API — Analytics Routes
"""
from flask import Blueprint
from app.controllers import analytics_controller
from app.middleware import roles_required

bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@bp.route("/platform-breakdown", methods=["GET"])
@roles_required("admin", "member")
def get_platform_breakdown():
    return analytics_controller.get_platform_breakdown()


@bp.route("/top-videos", methods=["GET"])
@roles_required("admin", "member")
def get_top_videos():
    return analytics_controller.get_top_videos()


@bp.route("/engagement-trends", methods=["GET"])
@roles_required("admin", "member")
def get_engagement_trends():
    return analytics_controller.get_engagement_trends()
