"""
Social Pulse API — Dashboard Routes
"""
from flask import Blueprint
from app.controllers import dashboard_controller
from app.middleware import roles_required

bp = Blueprint("dashboard", __name__, url_prefix="/api/me")


@bp.route("/dashboard", methods=["GET"])
@roles_required("admin", "member")
def get_dashboard():
    return dashboard_controller.get_dashboard()


@bp.route("/dashboard/pdf", methods=["GET"])
@roles_required("admin", "member")
def export_dashboard_pdf():
    return dashboard_controller.export_dashboard_pdf()
