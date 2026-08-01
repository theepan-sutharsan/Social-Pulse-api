"""
Social Pulse API — Multi-Platform Analytics Routes
Exposes GET /api/accounts/<id>/*, POST /api/competitors/compare, and GET /api/posts/<id>/* endpoints.
"""
from flask import Blueprint
from app.middleware import jwt_or_api_key_required
from app.controllers import multiplatform_analytics_controller

bp_accounts = Blueprint("multiplatform_accounts", __name__, url_prefix="/api/accounts")
bp_competitors = Blueprint("multiplatform_competitors", __name__, url_prefix="/api/competitors")
bp_posts = Blueprint("multiplatform_posts", __name__, url_prefix="/api/posts")


# Accounts endpoints
@bp_accounts.route("/<int:account_id>/growth", methods=["GET"])
@jwt_or_api_key_required
def get_account_growth(account_id: int):
    return multiplatform_analytics_controller.get_account_growth(account_id)


@bp_accounts.route("/<int:account_id>/predictions", methods=["GET"])
@jwt_or_api_key_required
def get_account_predictions(account_id: int):
    return multiplatform_analytics_controller.get_account_predictions(account_id)


@bp_accounts.route("/<int:account_id>/competitors", methods=["GET"])
@jwt_or_api_key_required
def get_account_competitors(account_id: int):
    return multiplatform_analytics_controller.get_account_competitors(account_id)


# Competitors compare endpoint
@bp_competitors.route("/compare", methods=["POST"])
@jwt_or_api_key_required
def compare_competitors():
    return multiplatform_analytics_controller.compare_competitors()


# Posts endpoints
@bp_posts.route("/<int:post_id>/analytics", methods=["GET"])
@jwt_or_api_key_required
def get_post_analytics(post_id: int):
    return multiplatform_analytics_controller.get_post_analytics(post_id)


@bp_posts.route("/<int:post_id>/seo", methods=["GET"])
@jwt_or_api_key_required
def get_post_seo(post_id: int):
    return multiplatform_analytics_controller.get_post_seo(post_id)


@bp_posts.route("/<int:post_id>/prediction", methods=["GET"])
@jwt_or_api_key_required
def get_post_prediction(post_id: int):
    return multiplatform_analytics_controller.get_post_prediction(post_id)
