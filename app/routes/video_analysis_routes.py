"""
Social Pulse API — Video Analysis Routes
"""
from flask import Blueprint
from app.controllers import video_analysis_controller
from app.middleware import roles_required

bp = Blueprint("video_analysis", __name__, url_prefix="/api/video-analysis")


@bp.route("/analyze", methods=["POST"])
@roles_required("admin", "member")
def analyze_video():
    return video_analysis_controller.analyze_video()


@bp.route("/history", methods=["GET"])
@roles_required("admin", "member")
def get_history():
    return video_analysis_controller.get_history()


@bp.route("/transcript", methods=["POST"])
@roles_required("admin", "member")
def get_transcript():
    return video_analysis_controller.get_transcript()


@bp.route("/<int:analysis_id>", methods=["GET"])
@roles_required("admin", "member")
def get_analysis_detail(analysis_id: int):
    return video_analysis_controller.get_analysis_detail(analysis_id)
