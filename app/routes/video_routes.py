"""
Social Pulse API — Video Routes
"""
from flask import Blueprint, request
from app.controllers import video_controller
from app.middleware import roles_required

bp = Blueprint("videos", __name__, url_prefix="/api/videos")


@bp.route("", methods=["GET"])
@roles_required("admin", "member")
def get_videos():
    return video_controller.get_videos()


@bp.route("/export", methods=["GET"])
@roles_required("admin", "member")
def export_videos():
    fmt = request.args.get("format", "csv")
    return video_controller.export_videos(fmt)


@bp.route("/<int:video_id>", methods=["GET"])
@roles_required("admin", "member")
def get_video(video_id: int):
    return video_controller.get_video(video_id)


@bp.route("/<int:video_id>/metrics", methods=["GET"])
@roles_required("admin", "member")
def get_video_metrics(video_id: int):
    return video_controller.get_video_metrics(video_id)


@bp.route("/<int:video_id>/thumbnail-analysis", methods=["POST"])
@roles_required("admin", "member")
def create_thumbnail_analysis(video_id: int):
    from app.controllers import thumbnail_controller
    return thumbnail_controller.create_thumbnail_analysis(video_id)


@bp.route("/<int:video_id>/thumbnail-analysis", methods=["GET"])
@roles_required("admin", "member")
def get_thumbnail_analysis(video_id: int):
    from app.controllers import thumbnail_controller
    return thumbnail_controller.get_thumbnail_analysis(video_id)
