"""
Social Pulse API — TrackedChannel Model
Enhanced with description, subscriber_count, total_views, profile_image, country, keywords, upload_playlist_id.
"""
from app.extensions import db
from app.utils import utc_now


class TrackedChannel(db.Model):
    __tablename__ = "tracked_channels"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    added_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    platform = db.Column(db.Enum("youtube"), nullable=False, default="youtube")
    channel_id = db.Column(db.String(255), nullable=False, unique=True)
    channel_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    subscriber_count = db.Column(db.BigInteger, nullable=True, default=0)
    total_views = db.Column(db.BigInteger, nullable=True, default=0)
    total_videos_count = db.Column(db.Integer, nullable=True, default=0)
    profile_image = db.Column(db.String(1000), nullable=True)
    banner_url = db.Column(db.String(1000), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    keywords = db.Column(db.Text, nullable=True)
    upload_playlist_id = db.Column(db.String(255), nullable=True)
    channel_created_at = db.Column(db.DateTime, nullable=True)
    niche = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    # Relationships
    videos = db.relationship(
        "Video", backref="tracked_channel", lazy=True, cascade="all, delete-orphan",
        foreign_keys="Video.tracked_channel_id",
    )
    suggestions = db.relationship(
        "Suggestion", backref="tracked_channel", lazy=True,
        foreign_keys="Suggestion.tracked_channel_id",
    )
    history = db.relationship(
        "ChannelHistory", backref="channel", lazy=True, cascade="all, delete-orphan",
        primaryjoin="TrackedChannel.channel_id == foreign(ChannelHistory.channel_id)"
    )

    @classmethod
    def get_by_channel_id(cls, channel_id: str):
        return cls.query.filter_by(channel_id=channel_id).first()

    @classmethod
    def get_by_niche(cls, niche: str):
        return cls.query.filter(cls.niche.ilike(f"%{niche}%")).all()

    @property
    def video_count(self) -> int:
        return self.total_videos_count or len(self.videos)

    def __repr__(self):
        return f"<TrackedChannel id={self.id} channel_id={self.channel_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "added_by_id": self.added_by_id,
            "platform": self.platform,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "description": self.description,
            "subscriber_count": self.subscriber_count or 0,
            "total_views": self.total_views or 0,
            "video_count": self.video_count,
            "profile_image": self.profile_image,
            "banner_url": self.banner_url,
            "country": self.country,
            "keywords": self.keywords,
            "upload_playlist_id": self.upload_playlist_id,
            "niche": self.niche,
            "channel_created_at": self.channel_created_at.isoformat() if self.channel_created_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
