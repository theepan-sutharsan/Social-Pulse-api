"""
Social Pulse API — Blueprint Registration
"""
from app.routes import (
    auth_routes,
    account_routes,
    tracked_channel_routes,
    video_routes,
    suggestion_routes,
    alert_routes,
    dashboard_routes,
    admin_user_routes,
    analytics_routes,
)


def register_blueprints(app):
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(account_routes.bp)
    app.register_blueprint(tracked_channel_routes.bp)
    app.register_blueprint(video_routes.bp)
    app.register_blueprint(suggestion_routes.bp)
    app.register_blueprint(alert_routes.bp)
    app.register_blueprint(dashboard_routes.bp)
    app.register_blueprint(admin_user_routes.bp)
    app.register_blueprint(analytics_routes.bp)
