"""
Social Pulse API — Alert Routes (stretch)
"""
from flask import Blueprint
from app.controllers import alert_controller
from app.middleware import roles_required

bp = Blueprint("alerts", __name__, url_prefix="/api/alerts")


@bp.route("", methods=["GET"])
@roles_required("member")
def get_alerts():
    return alert_controller.get_alerts()


@bp.route("/<int:alert_id>/read", methods=["PATCH"])
@roles_required("member")
def mark_alert_read(alert_id: int):
    return alert_controller.mark_alert_read(alert_id)
