"""
Social Pulse API — Configuration
"""
import os
from datetime import timedelta


class Config:
    # Database configuration with intelligent SQLite fallback
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "social_pulse")

    USE_SQLITE = os.getenv("USE_SQLITE", "0") == "1"
    
    if USE_SQLITE:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(os.path.dirname(__file__), '..', 'social_pulse.db')}"
    else:
        # Check if custom DB URI provided, otherwise default to MySQL with SQLite fallback if MySQL fails
        db_uri = os.getenv("DATABASE_URL")
        if db_uri:
            SQLALCHEMY_DATABASE_URI = db_uri
        else:
            SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "1440"))
    )

    # Flask
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-flask-secret")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
    PASSWORD_RESET_TOKEN_MAX_AGE = int(os.getenv("PASSWORD_RESET_TOKEN_MAX_AGE", "3600"))
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "1") == "1"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "0") == "1"
    # Comma-separated browser origins for Flask-CORS. Keep `*` as the default
    # for backwards-compatible local development; Railway should set this to
    # the Vercel deployment origin(s) in production.
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # Platform API keys
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
    META_APP_ID = os.getenv("META_APP_ID", "")
    META_APP_SECRET = os.getenv("META_APP_SECRET", "")
    META_REDIRECT_URI = os.getenv("META_REDIRECT_URI", "http://localhost:5000/api/accounts/oauth-callback")
    TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
    TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
    TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "http://localhost:5000/api/accounts/oauth-callback")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    GEMINI_API_KEY = GOOGLE_API_KEY
    GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")

    # YouTube audience-intelligence processing limits.  The worker contract
    # remains stage-based so it can move to Celery without changing the API.
    AUDIENCE_MAX_COMMENTS = int(os.getenv("AUDIENCE_MAX_COMMENTS", "10000"))
    AUDIENCE_COMMENT_BATCH_SIZE = int(os.getenv("AUDIENCE_COMMENT_BATCH_SIZE", "150"))
