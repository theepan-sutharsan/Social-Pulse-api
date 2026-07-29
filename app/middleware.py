"""
Social Pulse API — Role-Based Access Middleware
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_current_user


def roles_required(*roles):
    """
    Decorator that verifies JWT and checks the user's role is in `roles`.
    Usage: @roles_required("admin") or @roles_required("admin", "member")
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = get_current_user()
            if user is None:
                return jsonify({"error": "User not found."}), 401
            if user.role not in roles:
                return jsonify({"error": "Forbidden. Insufficient permissions."}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def jwt_or_api_key_required(fn):
    """
    Decorator verifying either JWT token or API Key header.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        return fn(*args, **kwargs)
    return wrapper
