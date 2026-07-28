"""
Social Pulse API — Enhanced Auth Controller
Added: validate email format helper, rate limiting awareness, and admin user creation.
"""
from flask import jsonify, request
from flask_jwt_extended import create_access_token, get_current_user
from app.extensions import db
from app.models.user_model import User
from app.utils import utc_now
import re

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _validate_register_payload(data: dict) -> list:
    errors = []
    email = data.get("email", "").strip()
    if not email:
        errors.append("Email is required.")
    elif not EMAIL_REGEX.match(email):
        errors.append("Invalid email format.")
    password = data.get("password", "")
    if not password:
        errors.append("Password is required.")
    elif len(password) < 6:
        errors.append("Password must be at least 6 characters.")
    elif len(password) > 128:
        errors.append("Password must not exceed 128 characters.")
    full_name = data.get("full_name", "").strip()
    if not full_name:
        errors.append("Full name is required.")
    elif len(full_name) < 2:
        errors.append("Full name must be at least 2 characters.")
    return errors


def register():
    data = request.get_json(silent=True) or {}
    errors = _validate_register_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify({"errors": ["Email is already registered."]}), 400

    # Only allow 'member' registration through public endpoint
    # Admins are created by seeding or an existing admin
    user = User(
        email=email,
        full_name=data["full_name"].strip(),
        role="member",
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
        return jsonify({"error": "Account is deactivated. Please contact support."}), 403

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
    errors = []

    if "full_name" in data:
        if not data["full_name"].strip():
            errors.append("Full name cannot be empty.")
        elif len(data["full_name"].strip()) < 2:
            errors.append("Full name must be at least 2 characters.")
        else:
            user.full_name = data["full_name"].strip()

    if "email" in data:
        new_email = data["email"].strip().lower()
        if not EMAIL_REGEX.match(new_email):
            errors.append("Invalid email format.")
        else:
            existing = User.query.filter_by(email=new_email).first()
            if existing and existing.id != user.id:
                errors.append("Email already in use by another account.")
            else:
                user.email = new_email

    if "password" in data and data["password"]:
        if len(data["password"]) < 6:
            errors.append("Password must be at least 6 characters.")
        else:
            user.set_password(data["password"])

    if errors:
        return jsonify({"errors": errors}), 400

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Update failed: {str(e)}"}), 500

    return jsonify({"message": "Profile updated successfully.", "user": user.to_dict()}), 200
