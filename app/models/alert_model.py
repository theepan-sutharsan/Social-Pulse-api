"""
Social Pulse API — Alert Model (stretch — competitor viral / milestone alerts)
"""
from app.extensions import db
from app.utils import utc_now


class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    type = db.Column(
        db.Enum("competitor_viral", "milestone"), nullable=False
    )
    message = db.Column(db.Text, nullable=False)
    related_video_id = db.Column(
        db.Integer, db.ForeignKey("videos.id"), nullable=True
    )
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "message": self.message,
            "related_video_id": self.related_video_id,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
