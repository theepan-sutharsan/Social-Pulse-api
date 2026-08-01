"""
Social Pulse API — Video Analysis Model
Stores YouTube video analysis results, transcript, thumbnail feedback, and AI recommendations.
"""
import json
from app.extensions import db
from app.utils import utc_now


class VideoAnalysis(db.Model):
    __tablename__ = "video_analyses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    youtube_url = db.Column(db.String(512), nullable=False)
    video_title = db.Column(db.String(512), nullable=True)
    transcript = db.Column(db.Text, nullable=True)
    analysis_json = db.Column(db.JSON, nullable=True)
    thumbnail_analysis_json = db.Column(db.JSON, nullable=True)
    overall_score = db.Column(db.Float, nullable=True, default=0.0)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    @classmethod
    def get_by_user(cls, user_id: int, limit: int = 50):
        return (
            cls.query.filter_by(user_id=user_id)
            .order_by(cls.created_at.desc())
            .limit(limit)
            .all()
        )

    def to_dict(self):
        analysis = self.analysis_json
        if isinstance(analysis, str):
            try:
                analysis = json.loads(analysis)
            except Exception:
                pass

        thumbnail_analysis = self.thumbnail_analysis_json
        if isinstance(thumbnail_analysis, str):
            try:
                thumbnail_analysis = json.loads(thumbnail_analysis)
            except Exception:
                pass

        return {
            "id": self.id,
            "user_id": self.user_id,
            "youtube_url": self.youtube_url,
            "video_title": self.video_title,
            "transcript": self.transcript,
            "analysis_json": analysis,
            "thumbnail_analysis_json": thumbnail_analysis,
            "overall_score": self.overall_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<VideoAnalysis id={self.id} user_id={self.user_id} title='{self.video_title}'>"
