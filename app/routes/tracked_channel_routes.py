"""
Social Pulse API — Tracked Channel Routes
"""
from flask import Blueprint, request
from app.controllers import tracked_channel_controller
from app.middleware import roles_required

bp = Blueprint("tracked_channels", __name__, url_prefix="/api/tracked-channels")


@bp.route("", methods=["GET"])
@roles_required("admin", "member")
def get_tracked_channels():
    return tracked_channel_controller.get_tracked_channels()


@bp.route("", methods=["POST"])
@roles_required("admin")
def create_tracked_channel():
    return tracked_channel_controller.create_tracked_channel()


@bp.route("/<int:channel_id>", methods=["GET"])
@roles_required("admin", "member")
def get_tracked_channel(channel_id: int):
    return tracked_channel_controller.get_tracked_channel(channel_id)


@bp.route("/<int:channel_id>", methods=["DELETE"])
@roles_required("admin")
def delete_tracked_channel(channel_id: int):
    return tracked_channel_controller.delete_tracked_channel(channel_id)


@bp.route("/<int:channel_id>/sync", methods=["POST"])
@roles_required("admin")
def sync_tracked_channel(channel_id: int):
    return tracked_channel_controller.sync_tracked_channel(channel_id)


@bp.route("/export", methods=["GET"])
@roles_required("admin")
def export_tracked_channels():
    fmt = request.args.get("format", "csv")
    return tracked_channel_controller.export_tracked_channels(fmt)


@bp.route("/import", methods=["POST"])
@roles_required("admin")
def import_tracked_channels_csv():
    if "file" not in request.files:
        from flask import jsonify
        return jsonify({"errors": ["No file provided. Use field name 'file'."]}), 400
    return tracked_channel_controller.import_tracked_channels_csv(request.files["file"])
