"""
Social Pulse API — ChannelHistory Model
Stores daily historical snapshots of YouTube public channel metrics (subscribers, total views, video count).
"""
from app.extensions import db
from app.utils import utc_now


class ChannelHistory(db.Model):
    __tablename__ = "channel_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    channel_id = db.Column(db.String(255), db.ForeignKey("tracked_channels.channel_id"), nullable=False, index=True)
    subscribers = db.Column(db.BigInteger, nullable=False, default=0)
    total_views = db.Column(db.BigInteger, nullable=False, default=0)
    total_videos = db.Column(db.Integer, nullable=False, default=0)
    recorded_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    @classmethod
    def get_history_for_channel(cls, channel_id: str, limit: int = 365):
        return (
            cls.query.filter_by(channel_id=str(channel_id))
            .order_by(cls.recorded_at.asc())
            .limit(limit)
            .all()
        )

    def to_dict(self):
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "subscribers": self.subscribers,
            "total_views": self.total_views,
            "total_videos": self.total_videos,
            "date": self.recorded_at.strftime("%Y-%m-%d") if self.recorded_at else None,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
