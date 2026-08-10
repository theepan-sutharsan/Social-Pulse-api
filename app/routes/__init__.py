"""
Social Pulse API — Blueprint Registration
"""


def register_blueprints(app):
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
        health_routes,
        channel_analytics_routes,
        video_analytics_routes,
        multiplatform_analytics_routes,
        video_analysis_routes,
        yt_channel_analysis_routes,
        youtube_audience_routes,
    )
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(account_routes.bp)
    app.register_blueprint(tracked_channel_routes.bp)
    app.register_blueprint(video_routes.bp)
    app.register_blueprint(suggestion_routes.bp)
    app.register_blueprint(alert_routes.bp)
    app.register_blueprint(dashboard_routes.bp)
    app.register_blueprint(admin_user_routes.bp)
    app.register_blueprint(analytics_routes.bp)
    app.register_blueprint(health_routes.bp)
    app.register_blueprint(channel_analytics_routes.bp)
    app.register_blueprint(video_analytics_routes.bp)
    app.register_blueprint(video_analysis_routes.bp)
    app.register_blueprint(multiplatform_analytics_routes.bp_accounts)
    app.register_blueprint(multiplatform_analytics_routes.bp_competitors)
    app.register_blueprint(multiplatform_analytics_routes.bp_posts)
    app.register_blueprint(yt_channel_analysis_routes.bp)
    app.register_blueprint(youtube_audience_routes.bp)

