"""
Social Pulse API — Suggestion Routes
"""
from flask import Blueprint
from app.controllers import suggestion_controller
from app.middleware import roles_required

bp = Blueprint("suggestions", __name__, url_prefix="/api/suggestions")


@bp.route("", methods=["POST"])
@roles_required("admin", "member")
def generate_suggestion():
    return suggestion_controller.generate_suggestion()


@bp.route("", methods=["GET"])
@roles_required("admin", "member")
def get_suggestions():
    return suggestion_controller.get_suggestions()


@bp.route("/export", methods=["GET"])
@roles_required("admin", "member")
def export_suggestions_csv():
    return suggestion_controller.export_suggestions_csv()


@bp.route("/<int:suggestion_id>", methods=["GET"])
@roles_required("admin", "member")
def get_suggestion(suggestion_id: int):
    return suggestion_controller.get_suggestion(suggestion_id)


@bp.route("/<int:suggestion_id>", methods=["DELETE"])
@roles_required("admin", "member")
def delete_suggestion(suggestion_id: int):
    return suggestion_controller.delete_suggestion(suggestion_id)


@bp.route("/<int:suggestion_id>/pdf", methods=["GET"])
@roles_required("admin", "member")
def export_suggestion_pdf(suggestion_id: int):
    return suggestion_controller.export_suggestion_pdf(suggestion_id)
