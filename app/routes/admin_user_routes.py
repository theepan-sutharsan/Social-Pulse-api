"""
Social Pulse API — Admin User Routes
"""
from flask import Blueprint
from app.controllers import admin_user_controller
from app.middleware import roles_required

bp = Blueprint("admin_users", __name__, url_prefix="/api/admin/users")


@bp.route("", methods=["GET"])
@roles_required("admin")
def get_all_users():
    return admin_user_controller.get_all_users()


@bp.route("/export", methods=["GET"])
@roles_required("admin")
def export_users_csv():
    return admin_user_controller.export_users_csv()


@bp.route("/<int:user_id>", methods=["GET"])
@roles_required("admin")
def get_user(user_id: int):
    return admin_user_controller.get_user(user_id)


@bp.route("/<int:user_id>", methods=["PUT"])
@roles_required("admin")
def update_user(user_id: int):
    return admin_user_controller.update_user(user_id)


@bp.route("/<int:user_id>/deactivate", methods=["POST"])
@roles_required("admin")
def deactivate_user(user_id: int):
    return admin_user_controller.deactivate_user(user_id)
