"""
Social Pulse API — Account Routes
"""
from flask import Blueprint, request
from app.controllers import account_controller
from app.middleware import roles_required

bp = Blueprint("accounts", __name__, url_prefix="/api/accounts")


@bp.route("", methods=["GET"])
@roles_required("admin", "member")
def get_accounts():
    return account_controller.get_accounts()


@bp.route("/youtube", methods=["POST"])
@roles_required("admin", "member")
def connect_youtube():
    return account_controller.connect_youtube()


@bp.route("/instagram/oauth-url", methods=["GET"])
@roles_required("admin", "member")
def get_instagram_oauth_url():
    return account_controller.get_instagram_oauth_url()


@bp.route("/facebook/oauth-url", methods=["GET"])
@roles_required("admin", "member")
def get_facebook_oauth_url():
    return account_controller.get_facebook_oauth_url()


@bp.route("/tiktok/oauth-url", methods=["GET"])
@roles_required("admin", "member")
def get_tiktok_oauth_url():
    return account_controller.get_tiktok_oauth_url()


@bp.route("/oauth-callback", methods=["GET", "POST"])
def oauth_callback():
    return account_controller.oauth_callback()


@bp.route("/<int:account_id>", methods=["DELETE"])
@roles_required("admin", "member")
def delete_account(account_id: int):
    return account_controller.delete_account(account_id)


@bp.route("/<int:account_id>/sync", methods=["POST"])
@roles_required("admin", "member")
def sync_account(account_id: int):
    return account_controller.sync_account(account_id)


@bp.route("/export", methods=["GET"])
@roles_required("admin")
def export_accounts_csv():
    return account_controller.export_accounts_csv()
