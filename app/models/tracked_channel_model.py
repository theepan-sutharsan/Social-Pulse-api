"""
Social Pulse API — TrackedChannel Model (v2)
Enhanced with: get_by_channel_id, video_count property.
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

    @classmethod
    def get_by_channel_id(cls, channel_id: str):
        return cls.query.filter_by(channel_id=channel_id).first()

    @classmethod
    def get_by_niche(cls, niche: str):
        return cls.query.filter(cls.niche.ilike(f"%{niche}%")).all()

    @property
    def video_count(self) -> int:
        return len(self.videos)

    def __repr__(self):
        return f"<TrackedChannel id={self.id} channel_id={self.channel_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "added_by_id": self.added_by_id,
            "platform": self.platform,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "niche": self.niche,
            "video_count": self.video_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
