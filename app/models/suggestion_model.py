"""
Social Pulse API — Suggestion Model
AI-generated content suggestions from patterns in videos.
"""
from app.extensions import db
from app.utils import utc_now


class Suggestion(db.Model):
    __tablename__ = "suggestions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    connected_account_id = db.Column(
        db.Integer, db.ForeignKey("connected_accounts.id"), nullable=True
    )
    tracked_channel_id = db.Column(
        db.Integer, db.ForeignKey("tracked_channels.id"), nullable=True
    )
    type = db.Column(
        db.Enum(
            "title", "caption", "hook", "hashtag",
            "thumbnail_concept", "posting_time", "content_calendar"
        ),
        nullable=False,
    )
    input_context = db.Column(db.Text, nullable=True)
    output = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    # Relationships
    sources = db.relationship(
        "SuggestionSource", backref="suggestion", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "connected_account_id": self.connected_account_id,
            "tracked_channel_id": self.tracked_channel_id,
            "type": self.type,
            "input_context": self.input_context,
            "output": self.output,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
