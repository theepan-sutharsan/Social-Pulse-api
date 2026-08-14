"""
Social Pulse API — Auth Routes
"""
from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.controllers import auth_controller

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.route("/register", methods=["POST"])
def register():
    return auth_controller.register()


@bp.route("/login", methods=["POST"])
def login():
    return auth_controller.login()


@bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    return auth_controller.request_password_reset()


@bp.route("/reset-password", methods=["POST"])
def reset_password():
    return auth_controller.reset_password()


@bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    return auth_controller.logout()


@bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    return auth_controller.get_profile()


@bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    return auth_controller.update_profile()
