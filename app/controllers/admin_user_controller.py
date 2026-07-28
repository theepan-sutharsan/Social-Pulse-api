"""
Social Pulse API — Admin User Management Controller
"""
from flask import jsonify, request
from flask_jwt_extended import get_current_user
from app.extensions import db
from app.models.user_model import User
from app.utils import utc_now
from app.utils.csv_utils import rows_to_csv_response
from datetime import date


def get_all_users():
    """Admin: list all users."""
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({"users": [u.to_dict() for u in users]}), 200


def get_user(user_id: int):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404
    return jsonify({"user": user.to_dict()}), 200


def update_user(user_id: int):
    """Admin: update user role or active status."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    data = request.get_json(silent=True) or {}
    if "role" in data and data["role"] in ("admin", "member"):
        user.role = data["role"]
    if "is_active" in data:
        user.is_active = bool(data["is_active"])
    if "full_name" in data and data["full_name"].strip():
        user.full_name = data["full_name"].strip()

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Update failed: {str(e)}"}), 500

    return jsonify({"message": "User updated.", "user": user.to_dict()}), 200


def deactivate_user(user_id: int):
    """Admin: deactivate a user account."""
    current = get_current_user()
    if current.id == user_id:
        return jsonify({"error": "Cannot deactivate your own account."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    user.is_active = False
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Deactivation failed: {str(e)}"}), 500

    return jsonify({"message": "User deactivated.", "user": user.to_dict()}), 200


def export_users_csv():
    """Admin: export all users as CSV."""
    users = User.query.order_by(User.created_at.desc()).all()
    headers = ["id", "email", "full_name", "role", "is_active", "created_at"]
    rows = [
        [u.id, u.email, u.full_name, u.role, u.is_active, u.created_at.isoformat() if u.created_at else ""]
        for u in users
    ]
    filename = f"users-{date.today().isoformat()}.csv"
    return rows_to_csv_response(filename, headers, rows)
