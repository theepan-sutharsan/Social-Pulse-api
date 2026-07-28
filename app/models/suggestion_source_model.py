"""
Social Pulse API — SuggestionSource Model (SIGNATURE many-to-many junction)
Links a Suggestion to the Videos whose patterns informed it.
"""
from app.extensions import db
from app.utils import utc_now


class SuggestionSource(db.Model):
    __tablename__ = "suggestion_sources"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    suggestion_id = db.Column(
        db.Integer, db.ForeignKey("suggestions.id"), nullable=False
    )
    video_id = db.Column(
        db.Integer, db.ForeignKey("videos.id"), nullable=False
    )
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        db.UniqueConstraint("suggestion_id", "video_id", name="uq_suggestion_video"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "suggestion_id": self.suggestion_id,
            "video_id": self.video_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
