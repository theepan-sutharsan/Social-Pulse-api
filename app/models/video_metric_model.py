"""
Social Pulse API — VideoMetric Model
Time-series snapshots of video performance metrics.
"""
from app.extensions import db
from app.utils import utc_now


class VideoMetric(db.Model):
    __tablename__ = "video_metrics"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    views = db.Column(db.BigInteger, nullable=True, default=0)
    likes = db.Column(db.Integer, nullable=True, default=0)
    comments = db.Column(db.Integer, nullable=True, default=0)
    shares = db.Column(db.Integer, nullable=True, default=0)
    engagement_rate = db.Column(db.Float, nullable=True, default=0.0)
    recorded_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    def to_dict(self):
        return {
            "id": self.id,
            "video_id": self.video_id,
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "engagement_rate": self.engagement_rate,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }
