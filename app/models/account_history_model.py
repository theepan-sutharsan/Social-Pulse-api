"""
Social Pulse API — AccountHistory Model
Stores daily historical snapshots of multi-platform accounts (YouTube, Instagram, Facebook, TikTok, X, LinkedIn).
"""
from app.extensions import db
from app.utils import utc_now


class AccountHistory(db.Model):
    __tablename__ = "account_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account_id = db.Column(db.Integer, db.ForeignKey("connected_accounts.id"), nullable=True, index=True)
    platform = db.Column(db.Enum("youtube", "instagram", "facebook", "tiktok", "twitter", "linkedin"), nullable=False, index=True)
    platform_account_id = db.Column(db.String(255), nullable=False, index=True)
    followers = db.Column(db.BigInteger, nullable=False, default=0)
    following = db.Column(db.BigInteger, nullable=False, default=0)
    total_views = db.Column(db.BigInteger, nullable=False, default=0)
    total_posts = db.Column(db.Integer, nullable=False, default=0)
    recorded_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    @classmethod
    def get_history_for_account(cls, platform_account_id: str, platform: str = None, limit: int = 365):
        """Fetch historical snapshots for an account ordered by date ascending."""
        q = cls.query.filter_by(platform_account_id=str(platform_account_id))
        if platform:
            q = q.filter_by(platform=platform)
        return q.order_by(cls.recorded_at.asc()).limit(limit).all()

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "platform": self.platform,
            "platform_account_id": self.platform_account_id,
            "followers": self.followers,
            "subscribers": self.followers,  # Alias for YouTube
            "following": self.following,
            "total_views": self.total_views,
            "total_posts": self.total_posts,
            "date": self.recorded_at.strftime("%Y-%m-%d") if self.recorded_at else None,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
