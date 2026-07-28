import re

def validate_registration(data: dict) -> list:
    errors = []
    email = data.get("email", "").strip()
    if not email:
        errors.append("Email is required.")
    elif "@" not in email:
        errors.append("Invalid email format.")
    password = data.get("password", "")
    if not password:
        errors.append("Password is required.")
    elif len(password) < 6:
        errors.append("Password must be at least 6 characters.")
    full_name = data.get("full_name", "").strip()
    if not full_name:
        errors.append("Full name is required.")
    return errors
