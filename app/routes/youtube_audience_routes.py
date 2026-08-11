"""YouTube Video Audience Intelligence API routes."""
from flask import Blueprint

from app.controllers import youtube_audience_controller as controller
from app.middleware import roles_required


bp = Blueprint("youtube_audience", __name__, url_prefix="/api/youtube-audience")


@bp.route("/estimate", methods=["POST"])
@roles_required("admin", "member")
def estimate():
    return controller.estimate()


@bp.route("/analyze", methods=["POST"])
@roles_required("admin", "member")
def start_analysis():
    return controller.start_analysis()


@bp.route("/history", methods=["GET"])
@roles_required("admin", "member")
def history():
    return controller.get_history()


@bp.route("/runs/<int:run_id>", methods=["GET"])
@roles_required("admin", "member")
def run_detail(run_id: int):
    return controller.get_run(run_id)


@bp.route("/runs/<int:run_id>", methods=["DELETE"])
@roles_required("admin", "member")
def delete_run(run_id: int):
    return controller.delete_run(run_id)


@bp.route("/runs/<int:run_id>/comments", methods=["GET"])
@roles_required("admin", "member")
def comments(run_id: int):
    return controller.get_comments(run_id)


@bp.route("/runs/<int:run_id>/export.csv", methods=["GET"])
@roles_required("admin", "member")
def csv_export(run_id: int):
    return controller.export_csv(run_id)


@bp.route("/runs/<int:run_id>/export.pdf", methods=["GET"])
@roles_required("admin", "member")
def pdf_export(run_id: int):
    return controller.export_pdf(run_id)


@bp.route("/videos/<video_id>/comments", methods=["DELETE"])
@roles_required("admin", "member")
def purge_comments(video_id: str):
    return controller.purge_video_comments(video_id)
