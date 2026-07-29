"""
Social Pulse API — VideoHistory Model
Stores daily historical snapshots of video performance metrics (views, likes, comments, shares).
"""
from app.extensions import db
from app.utils import utc_now


class VideoHistory(db.Model):
    __tablename__ = "video_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False, index=True)
    external_id = db.Column(db.String(255), nullable=True, index=True)
    views = db.Column(db.BigInteger, nullable=False, default=0)
    likes = db.Column(db.Integer, nullable=False, default=0)
    comments = db.Column(db.Integer, nullable=False, default=0)
    shares = db.Column(db.Integer, nullable=False, default=0)
    recorded_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    @classmethod
    def get_history_for_video(cls, video_id: int, limit: int = 365):
        return (
            cls.query.filter_by(video_id=video_id)
            .order_by(cls.recorded_at.asc())
            .limit(limit)
            .all()
        )

    def to_dict(self):
        return {
            "id": self.id,
            "video_id": self.video_id,
            "external_id": self.external_id,
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "date": self.recorded_at.strftime("%Y-%m-%d") if self.recorded_at else None,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
