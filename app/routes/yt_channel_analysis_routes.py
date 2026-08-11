"""
Social Pulse API — YouTube Channel Analysis Routes
"""
from flask import Blueprint
from app.controllers import yt_channel_analysis_controller
from app.middleware import roles_required

bp = Blueprint("yt_channel_analysis", __name__, url_prefix="/api/yt-channel-analysis")


@bp.route("/start", methods=["POST"])
@roles_required("admin", "member")
def start_analysis():
    return yt_channel_analysis_controller.start_analysis()


@bp.route("/history", methods=["GET"])
@roles_required("admin", "member")
def get_history():
    return yt_channel_analysis_controller.get_analysis_history()


@bp.route("/<int:run_id>", methods=["GET"])
@roles_required("admin", "member")
def get_run(run_id: int):
    return yt_channel_analysis_controller.get_analysis_run(run_id)


@bp.route("/<int:run_id>", methods=["DELETE"])
@roles_required("admin", "member")
def delete_run(run_id: int):
    return yt_channel_analysis_controller.delete_analysis_run(run_id)
