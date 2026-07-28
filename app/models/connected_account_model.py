"""
Social Pulse API — ConnectedAccount Model (v2)
Added: to_dict_with_video_count, is_youtube, is_oauth properties.
"""
from app.extensions import db
from app.utils import utc_now


class ConnectedAccount(db.Model):
    __tablename__ = "connected_accounts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    platform = db.Column(
        db.Enum("youtube", "instagram", "facebook", "tiktok"),
        nullable=False,
    )
    platform_account_id = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(255), nullable=False)
    access_token = db.Column(db.Text, nullable=True)
    refresh_token = db.Column(db.Text, nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    # Relationships
    videos = db.relationship(
        "Video", backref="connected_account", lazy=True, cascade="all, delete-orphan",
        foreign_keys="Video.connected_account_id",
    )
    suggestions = db.relationship(
        "Suggestion", backref="connected_account", lazy=True,
        foreign_keys="Suggestion.connected_account_id",
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "platform", "platform_account_id", name="uq_user_platform_account"),
    )

    @property
    def is_youtube(self) -> bool:
        return self.platform == "youtube"

    @property
    def is_oauth(self) -> bool:
        return self.platform in ("instagram", "facebook", "tiktok")

    @property
    def video_count(self) -> int:
        return len(self.videos)

    @property
    def is_token_expired(self) -> bool:
        if not self.token_expires_at:
            return False
        return utc_now() > self.token_expires_at

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "platform": self.platform,
            "platform_account_id": self.platform_account_id,
            "display_name": self.display_name,
            "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
            "is_token_expired": self.is_token_expired,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "video_count": self.video_count,
        }
