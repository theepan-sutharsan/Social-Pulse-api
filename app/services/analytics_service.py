from app.models.video_metric_model import VideoMetric

class AnalyticsService:
    @staticmethod
    def get_summary():
        return {"status": "analytics_active"}
