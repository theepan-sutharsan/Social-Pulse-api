"""
Social Pulse API — ThumbnailAnalysis Model (stretch — AI vision analysis)
"""
from app.extensions import db
from app.utils import utc_now


class ThumbnailAnalysis(db.Model):
    __tablename__ = "thumbnail_analyses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    video_id = db.Column(
        db.Integer, db.ForeignKey("videos.id"), nullable=False, unique=True
    )
    dominant_colors = db.Column(db.JSON, nullable=True)
    has_text = db.Column(db.Boolean, nullable=True)
    face_count = db.Column(db.Integer, nullable=True, default=0)
    composition_notes = db.Column(db.Text, nullable=True)
    score = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    def to_dict(self):
        return {
            "id": self.id,
            "video_id": self.video_id,
            "dominant_colors": self.dominant_colors,
            "has_text": self.has_text,
            "face_count": self.face_count,
            "composition_notes": self.composition_notes,
            "score": self.score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
