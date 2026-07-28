"""
Social Pulse API — VideoMetric Model (v2)
Enhanced with: average_for_video, engagement helper.
"""
from app.extensions import db
from app.utils import utc_now
from sqlalchemy import func


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

    @classmethod
    def latest_for_video(cls, video_id: int):
        return (
            cls.query.filter_by(video_id=video_id)
            .order_by(cls.recorded_at.desc())
            .first()
        )

    @classmethod
    def average_engagement_for_account(cls, video_ids: list) -> float:
        """Compute average engagement rate across a list of video IDs."""
        if not video_ids:
            return 0.0
        result = (
            db.session.query(func.avg(cls.engagement_rate))
            .filter(cls.video_id.in_(video_ids))
            .scalar()
        )
        return round(result or 0.0, 4)

    @classmethod
    def total_views_for_account(cls, video_ids: list) -> int:
        """Sum of the latest views across all videos."""
        if not video_ids:
            return 0
        total = 0
        for vid_id in video_ids:
            latest = cls.latest_for_video(vid_id)
            if latest and latest.views:
                total += latest.views
        return total

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
