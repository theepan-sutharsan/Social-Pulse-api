"""
Social Pulse API — Health Check Routes
"""
from flask import Blueprint, jsonify
from app.extensions import db

bp = Blueprint("health", __name__, url_prefix="/api")


@bp.route("/health", methods=["GET"])
def health_check():
    """Public health check endpoint."""
    try:
        db.session.execute(db.text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return jsonify({
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
        "app": "Social Pulse API",
        "version": "1.0.0",
    }), 200 if db_status == "ok" else 503


@bp.route("/", methods=["GET"])
def root():
    return jsonify({"message": "Welcome to Social Pulse API v1.0.0"}), 200
