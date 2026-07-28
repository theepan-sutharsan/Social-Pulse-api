"""
Social Pulse API — TrackedChannel Model
YouTube-only competitor/niche channels for comparison.
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

    def to_dict(self):
        return {
            "id": self.id,
            "added_by_id": self.added_by_id,
            "platform": self.platform,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "niche": self.niche,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
