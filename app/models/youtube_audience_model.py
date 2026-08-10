"""
Versioned YouTube audience-intelligence persistence.

The generic ``videos`` table remains the canonical video metadata cache.  The
tables in this module store comment snapshots and per-run classifications so a
new analysis never overwrites historical evidence.
"""
import json

from app.extensions import db
from app.utils import utc_now


def _json_value(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value
    return value


class AudienceAnalysisRun(db.Model):
    __tablename__ = "audience_analysis_runs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    video_fk_id = db.Column(db.Integer, db.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    external_video_id = db.Column(db.String(32), nullable=False, index=True)
    video_url = db.Column(db.String(512), nullable=False)
    status = db.Column(db.String(24), nullable=False, default="PENDING", index=True)
    requested_count = db.Column(db.Integer, nullable=True)
    requested_all = db.Column(db.Boolean, nullable=False, default=False)
    available_count = db.Column(db.Integer, nullable=False, default=0)
    fetched_count = db.Column(db.Integer, nullable=False, default=0)
    unique_count = db.Column(db.Integer, nullable=False, default=0)
    analyzed_count = db.Column(db.Integer, nullable=False, default=0)
    skipped_count = db.Column(db.Integer, nullable=False, default=0)
    failed_count = db.Column(db.Integer, nullable=False, default=0)
    current_stage = db.Column(db.String(32), nullable=False, default="PENDING")
    progress_pct = db.Column(db.Float, nullable=False, default=0.0)
    current_batch = db.Column(db.Integer, nullable=False, default=0)
    total_batches = db.Column(db.Integer, nullable=False, default=0)
    model_used = db.Column(db.String(80), nullable=True)
    configuration_json = db.Column(db.JSON, nullable=True)
    report_json = db.Column(db.JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    video = db.relationship("Video", backref=db.backref("audience_analysis_runs", lazy=True))
    comment_analyses = db.relationship(
        "AudienceCommentAnalysis",
        backref="run",
        lazy=True,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.Index("ix_audience_run_user_video_status", "user_id", "external_video_id", "status"),
    )

    @classmethod
    def get_by_user(cls, user_id: int, limit: int = 20):
        return (
            cls.query.filter_by(user_id=user_id)
            .order_by(cls.created_at.desc())
            .limit(limit)
            .all()
        )

    def to_dict(self, include_report: bool = True):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "video_id": self.external_video_id,
            "video_fk_id": self.video_fk_id,
            "video_url": self.video_url,
            "status": self.status,
            "requested_count": self.requested_count,
            "requested_all": bool(self.requested_all),
            "available_count": self.available_count or 0,
            "fetched_count": self.fetched_count or 0,
            "unique_count": self.unique_count or 0,
            "analyzed_count": self.analyzed_count or 0,
            "skipped_count": self.skipped_count or 0,
            "failed_count": self.failed_count or 0,
            "current_stage": self.current_stage,
            "progress_pct": round(float(self.progress_pct or 0), 2),
            "current_batch": self.current_batch or 0,
            "total_batches": self.total_batches or 0,
            "model_used": self.model_used,
            "configuration": _json_value(self.configuration_json),
            "report": _json_value(self.report_json) if include_report else None,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "video": self.video.to_dict(include_metrics=True) if self.video else None,
        }


class AudienceComment(db.Model):
    __tablename__ = "audience_comments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    video_fk_id = db.Column(db.Integer, db.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    external_comment_id = db.Column(db.String(255), nullable=False)
    parent_external_comment_id = db.Column(db.String(255), nullable=True, index=True)
    author_name = db.Column(db.String(255), nullable=True)
    author_channel_id = db.Column(db.String(255), nullable=True)
    original_text = db.Column(db.Text, nullable=False)
    normalized_text = db.Column(db.Text, nullable=False)
    like_count = db.Column(db.Integer, nullable=False, default=0)
    reply_count = db.Column(db.Integer, nullable=False, default=0)
    published_at = db.Column(db.DateTime, nullable=True, index=True)
    updated_at = db.Column(db.DateTime, nullable=True, index=True)
    first_seen_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)

    video = db.relationship("Video", backref=db.backref("audience_comments", lazy=True))
    analyses = db.relationship(
        "AudienceCommentAnalysis",
        backref="comment",
        lazy=True,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint("video_fk_id", "external_comment_id", name="uq_audience_video_comment"),
        db.Index("ix_audience_comment_video_published", "video_fk_id", "published_at"),
    )

    def to_dict(self, analysis=None):
        value = {
            "id": self.id,
            "comment_id": self.external_comment_id,
            "parent_comment_id": self.parent_external_comment_id,
            "author": self.author_name,
            "author_channel_id": self.author_channel_id,
            "text": self.original_text,
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "likes": self.like_count or 0,
            "replies": self.reply_count or 0,
            "is_deleted": bool(self.is_deleted),
        }
        if analysis:
            value.update(analysis.to_dict())
        return value


class AudienceCommentAnalysis(db.Model):
    __tablename__ = "audience_comment_analyses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    run_id = db.Column(db.Integer, db.ForeignKey("audience_analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    comment_id = db.Column(db.Integer, db.ForeignKey("audience_comments.id", ondelete="CASCADE"), nullable=False, index=True)
    language = db.Column(db.String(40), nullable=True)
    sentiment = db.Column(db.String(16), nullable=True)
    emotion = db.Column(db.String(32), nullable=True)
    topic = db.Column(db.String(120), nullable=True)
    intent = db.Column(db.String(64), nullable=True)
    persona = db.Column(db.String(64), nullable=True)
    cluster = db.Column(db.String(120), nullable=True)
    is_spam = db.Column(db.Boolean, nullable=False, default=False)
    is_toxic = db.Column(db.Boolean, nullable=False, default=False)
    toxicity_severity = db.Column(db.String(16), nullable=True)
    is_sarcastic = db.Column(db.Boolean, nullable=False, default=False)
    bot_signal = db.Column(db.String(32), nullable=True)
    quality_score = db.Column(db.Float, nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    evidence_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        db.UniqueConstraint("run_id", "comment_id", name="uq_audience_run_comment_analysis"),
        db.Index("ix_audience_analysis_filters", "run_id", "sentiment", "topic", "intent"),
    )

    def to_dict(self):
        return {
            "language": self.language,
            "sentiment": self.sentiment,
            "emotion": self.emotion,
            "topic": self.topic,
            "intent": self.intent,
            "persona": self.persona,
            "cluster": self.cluster,
            "spam": bool(self.is_spam),
            "toxicity": bool(self.is_toxic),
            "toxicity_severity": self.toxicity_severity,
            "sarcasm": bool(self.is_sarcastic),
            "bot_signal": self.bot_signal,
            "quality_score": round(float(self.quality_score or 0), 2),
            "confidence": round(float(self.confidence or 0), 3),
            "evidence": _json_value(self.evidence_json) or {},
        }
