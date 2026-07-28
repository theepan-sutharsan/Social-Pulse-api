"""
Social Pulse API — Token encryption/decryption for OAuth tokens stored in DB.
Uses Fernet symmetric encryption from the cryptography library.
"""
import base64
import os
from flask import current_app


def _get_fernet():
    """Get a Fernet instance from ENCRYPTION_KEY env var, or generate a temporary one."""
    try:
        from cryptography.fernet import Fernet
        key = current_app.config.get("ENCRYPTION_KEY", "")
        if not key:
            # For demo: generate ephemeral key (tokens won't survive restarts)
            key = Fernet.generate_key().decode()
        # Ensure key is properly padded base64
        if isinstance(key, str):
            key = key.encode()
        return Fernet(key)
    except Exception:
        return None


def encrypt_token(plain_token: str) -> str:
    """Encrypt a plain text OAuth token. Returns base64-encoded ciphertext."""
    if not plain_token:
        return plain_token
    fernet = _get_fernet()
    if not fernet:
        return plain_token  # Fallback: store plain (not recommended for production)
    try:
        return fernet.encrypt(plain_token.encode()).decode()
    except Exception:
        return plain_token


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt an encrypted OAuth token back to plain text."""
    if not encrypted_token:
        return encrypted_token
    fernet = _get_fernet()
    if not fernet:
        return encrypted_token
    try:
        return fernet.decrypt(encrypted_token.encode()).decode()
    except Exception:
        # Token may already be plain text (migration case)
        return encrypted_token
