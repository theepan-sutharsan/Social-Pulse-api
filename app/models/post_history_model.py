"""
Social Pulse API — PostHistory Model
Stores daily historical snapshots of posts, reels, tweets, and videos across platforms.
"""
from app.extensions import db
from app.utils import utc_now


class PostHistory(db.Model):
    __tablename__ = "post_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=True, index=True)
    external_id = db.Column(db.String(255), nullable=False, index=True)
    platform = db.Column(db.Enum("youtube", "instagram", "facebook", "tiktok", "twitter", "linkedin"), nullable=False, index=True)
    views = db.Column(db.BigInteger, nullable=False, default=0)
    likes = db.Column(db.Integer, nullable=False, default=0)
    comments = db.Column(db.Integer, nullable=False, default=0)
    shares = db.Column(db.Integer, nullable=False, default=0)
    reactions = db.Column(db.Integer, nullable=False, default=0)
    impressions = db.Column(db.BigInteger, nullable=False, default=0)
    recorded_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    @classmethod
    def get_history_for_post(cls, external_id: str, limit: int = 365):
        """Fetch historical snapshots for a post/video ordered by date ascending."""
        return (
            cls.query.filter_by(external_id=str(external_id))
            .order_by(cls.recorded_at.asc())
            .limit(limit)
            .all()
        )

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "external_id": self.external_id,
            "platform": self.platform,
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "reactions": self.reactions,
            "impressions": self.impressions,
            "date": self.recorded_at.strftime("%Y-%m-%d") if self.recorded_at else None,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
