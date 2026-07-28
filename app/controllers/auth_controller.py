"""
Social Pulse API — Auth Controller
Handles register, login, profile endpoints.
"""
from flask import jsonify, request
from flask_jwt_extended import create_access_token, get_current_user
from app.extensions import db
from app.models.user_model import User
from app.utils import utc_now


def _validate_register_payload(data: dict) -> list:
    errors = []
    if not data.get("email", "").strip():
        errors.append("Email is required.")
    elif "@" not in data["email"]:
        errors.append("Invalid email format.")
    if not data.get("password", ""):
        errors.append("Password is required.")
    elif len(data["password"]) < 6:
        errors.append("Password must be at least 6 characters.")
    if not data.get("full_name", "").strip():
        errors.append("Full name is required.")
    return errors


def register():
    data = request.get_json(silent=True) or {}
    errors = _validate_register_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify({"errors": ["Email is already registered."]}), 400

    user = User(
        email=email,
        full_name=data["full_name"].strip(),
        role=data.get("role", "member") if data.get("role") in ("admin", "member") else "member",
        is_active=True,
        created_at=utc_now(),
    )
    user.set_password(data["password"])

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

    token = create_access_token(identity=str(user.id))
    return jsonify({"message": "Registration successful.", "access_token": token, "user": user.to_dict()}), 201


def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"errors": ["Email and password are required."]}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password."}), 401
    if not user.is_active:
        return jsonify({"error": "Account is deactivated."}), 403

    token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": token, "user": user.to_dict()}), 200


def logout():
    return jsonify({"message": "Logged out successfully."}), 200


def get_profile():
    user = get_current_user()
    return jsonify({"user": user.to_dict()}), 200


def update_profile():
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    if "full_name" in data and data["full_name"].strip():
        user.full_name = data["full_name"].strip()
    if "email" in data and data["email"].strip():
        new_email = data["email"].strip().lower()
        existing = User.query.filter_by(email=new_email).first()
        if existing and existing.id != user.id:
            return jsonify({"error": "Email already in use."}), 400
        user.email = new_email
    if "password" in data and data["password"]:
        if len(data["password"]) < 6:
            return jsonify({"errors": ["Password must be at least 6 characters."]}), 400
        user.set_password(data["password"])

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Update failed: {str(e)}"}), 500

    return jsonify({"message": "Profile updated.", "user": user.to_dict()}), 200
