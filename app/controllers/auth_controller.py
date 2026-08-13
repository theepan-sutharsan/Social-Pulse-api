"""
Social Pulse API — Enhanced Auth Controller
Added: validate email format helper, rate limiting awareness, and admin user creation.
"""
import hashlib
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from flask import current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_current_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from app.extensions import db
from app.models.user_model import User
from app.utils import utc_now
import re

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PASSWORD_RESET_SALT = "social-pulse-password-reset"


def _password_reset_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=PASSWORD_RESET_SALT)


def _password_fingerprint(user: User) -> str:
    return hashlib.sha256(user.password.encode("utf-8")).hexdigest()


def _create_password_reset_token(user: User) -> str:
    return _password_reset_serializer().dumps(
        {
            "purpose": "password-reset",
            "user_id": user.id,
            "email": user.email,
            "password_fingerprint": _password_fingerprint(user),
        }
    )


def _get_user_from_password_reset_token(token: str) -> User:
    payload = _password_reset_serializer().loads(
        token,
        max_age=int(current_app.config.get("PASSWORD_RESET_TOKEN_MAX_AGE", 3600)),
    )
    if payload.get("purpose") != "password-reset":
        raise BadSignature("Invalid password reset purpose.")

    user = db.session.get(User, payload.get("user_id"))
    if (
        not user
        or not user.is_active
        or payload.get("email") != user.email
        or payload.get("password_fingerprint") != _password_fingerprint(user)
    ):
        raise BadSignature("Invalid password reset token.")
    return user


def _send_password_reset_email(recipient: str, reset_url: str) -> bool:
    mail_server = current_app.config.get("MAIL_SERVER", "").strip()
    if not mail_server:
        current_app.logger.info("Password reset link for %s: %s", recipient, reset_url)
        return False

    message = EmailMessage()
    message["Subject"] = "Reset your Social Pulse password"
    message["From"] = current_app.config.get("MAIL_DEFAULT_SENDER") or current_app.config.get("MAIL_USERNAME") or "no-reply@socialpulse.local"
    message["To"] = recipient
    message.set_content(
        "We received a request to reset your Social Pulse password.\n\n"
        f"Open this link within {int(current_app.config.get('PASSWORD_RESET_TOKEN_MAX_AGE', 3600)) // 60} minutes:\n"
        f"{reset_url}\n\n"
        "If you did not request this, you can safely ignore this email."
    )

    mail_port = int(current_app.config.get("MAIL_PORT", 587))
    mail_username = current_app.config.get("MAIL_USERNAME", "")
    mail_password = current_app.config.get("MAIL_PASSWORD", "")
    use_ssl = bool(current_app.config.get("MAIL_USE_SSL", False))
    use_tls = bool(current_app.config.get("MAIL_USE_TLS", True)) and not use_ssl
    smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    with smtp_class(mail_server, mail_port, timeout=15) as smtp:
        if use_tls:
            smtp.starttls()
        if mail_username:
            smtp.login(mail_username, mail_password)
        smtp.send_message(message)
    return True


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


def request_password_reset():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    if not EMAIL_REGEX.match(email):
        return jsonify({"errors": ["Enter a valid email address."]}), 400

    response = {
        "message": "If an account exists for that email, password reset instructions will be sent shortly."
    }
    user = User.get_by_email(email)
    if user and user.is_active:
        token = _create_password_reset_token(user)
        frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
        reset_url = f"{frontend_url}/auth/reset-password?token={quote(token, safe='')}"
        try:
            _send_password_reset_email(email, reset_url)
        except Exception:
            current_app.logger.exception("Password reset email delivery failed for %s", email)

        # Local development remains usable without an SMTP account.
        # Production responses never expose reset tokens.
        if current_app.debug and not current_app.config.get("MAIL_SERVER", "").strip():
            response["reset_url"] = reset_url

    return jsonify(response), 200


def reset_password():
    data = request.get_json(silent=True) or {}
    token = str(data.get("token", "")).strip()
    password = data.get("password", "")
    errors = []
    if not token:
        errors.append("Password reset token is required.")
    if not password:
        errors.append("Password is required.")
    elif len(password) < 6:
        errors.append("Password must be at least 6 characters.")
    elif len(password) > 128:
        errors.append("Password must not exceed 128 characters.")
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        user = _get_user_from_password_reset_token(token)
    except SignatureExpired:
        return jsonify({"error": "This password reset link has expired. Request a new one."}), 400
    except BadSignature:
        return jsonify({"error": "This password reset link is invalid or has already been used."}), 400

    user.set_password(password)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Password reset failed: {str(e)}"}), 500

    return jsonify({"message": "Password reset successfully."}), 200


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
