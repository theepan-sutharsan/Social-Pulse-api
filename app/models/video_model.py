"""
Social Pulse API — Video Model
Fetched video/post records from connected accounts or tracked channels.
"""
from app.extensions import db
from app.utils import utc_now


class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    connected_account_id = db.Column(
        db.Integer, db.ForeignKey("connected_accounts.id"), nullable=True
    )
    tracked_channel_id = db.Column(
        db.Integer, db.ForeignKey("tracked_channels.id"), nullable=True
    )
    platform = db.Column(
        db.Enum("youtube", "instagram", "facebook", "tiktok"),
        nullable=False,
    )
    external_id = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    tags = db.Column(db.JSON, nullable=True)
    thumbnail_url = db.Column(db.String(1000), nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)
    fetched_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    # Relationships
    metrics = db.relationship(
        "VideoMetric", backref="video", lazy=True, cascade="all, delete-orphan"
    )
    thumbnail_analysis = db.relationship(
        "ThumbnailAnalysis", backref="video", uselist=False, cascade="all, delete-orphan"
    )
    suggestion_sources = db.relationship(
        "SuggestionSource", backref="video", lazy=True, cascade="all, delete-orphan"
    )
    alerts = db.relationship(
        "Alert", backref="related_video", lazy=True, foreign_keys="Alert.related_video_id"
    )

    __table_args__ = (
        db.UniqueConstraint("platform", "external_id", name="uq_platform_external_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "connected_account_id": self.connected_account_id,
            "tracked_channel_id": self.tracked_channel_id,
            "platform": self.platform,
            "external_id": self.external_id,
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "thumbnail_url": self.thumbnail_url,
            "duration_seconds": self.duration_seconds,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
        }
