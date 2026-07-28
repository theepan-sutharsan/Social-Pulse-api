"""
Social Pulse API — Application Factory
"""
from flask import Flask, jsonify
from sqlalchemy.exc import OperationalError, ProgrammingError
from dotenv import load_dotenv

load_dotenv()

from app.config import Config
from app.extensions import db, jwt


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)

    # JWT user lookup
    from app.models.user_model import User

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return User.query.get(int(identity))

    # Register blueprints
    from app.routes import register_blueprints
    register_blueprints(app)

    # Create tables
    with app.app_context():
        # Import all models so SQLAlchemy sees them
        from app.models import (  # noqa: F401
            user_model,
            connected_account_model,
            tracked_channel_model,
            video_model,
            video_metric_model,
            suggestion_model,
            suggestion_source_model,
            thumbnail_analysis_model,
            alert_model,
        )
        try:
            db.create_all()
        except (OperationalError, ProgrammingError) as e:
            app.logger.error(f"Database error during create_all: {e}")

    # Global error handlers
    @app.errorhandler(OperationalError)
    def handle_db_operational_error(e):
        return jsonify({"error": "Database connection error. Please try again later."}), 503

    @app.errorhandler(ProgrammingError)
    def handle_db_programming_error(e):
        return jsonify({"error": "Database schema error. Please contact support."}), 500

    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({"error": "Resource not found."}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        return jsonify({"error": "Method not allowed."}), 405

    return app
