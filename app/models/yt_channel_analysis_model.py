"""
Social Pulse API — YouTube Channel Analysis Models
Stores channel metadata, per-video metadata, and analysis run results for
the YouTube Channel Video Analysis & AI Script Idea Generator feature.
"""
import json
from app.extensions import db
from app.utils import utc_now


class YTAnalyzedChannel(db.Model):
    """
    A YouTube channel submitted for analysis, scoped to a user.
    """
    __tablename__ = "yt_analyzed_channels"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel_id = db.Column(db.String(64), nullable=False)           # YouTube UC... ID
    channel_handle = db.Column(db.String(255), nullable=True)
    channel_title = db.Column(db.String(255), nullable=True)
    subscriber_count = db.Column(db.BigInteger, nullable=True, default=0)
    thumbnail_url = db.Column(db.Text, nullable=True)
    last_analyzed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    # Relationships
    videos = db.relationship("YTChannelVideo", backref="channel", lazy=True, cascade="all, delete-orphan")
    analysis_runs = db.relationship("YTChannelAnalysisRun", backref="channel", lazy=True, cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("user_id", "channel_id", name="uq_user_channel"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "channel_handle": self.channel_handle,
            "channel_title": self.channel_title,
            "subscriber_count": self.subscriber_count or 0,
            "thumbnail_url": self.thumbnail_url,
            "last_analyzed_at": self.last_analyzed_at.isoformat() if self.last_analyzed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<YTAnalyzedChannel id={self.id} channel_id={self.channel_id}>"


class YTChannelVideo(db.Model):
    """
    Raw metadata for each video fetched from a channel during an analysis run.
    Acts as a local cache to avoid re-fetching from YouTube API.
    """
    __tablename__ = "yt_channel_videos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    channel_fk_id = db.Column(db.Integer, db.ForeignKey("yt_analyzed_channels.id", ondelete="CASCADE"), nullable=False)
    video_id = db.Column(db.String(32), nullable=False)             # YouTube video ID
    title = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    tags_json = db.Column(db.JSON, nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True, default=0)
    view_count = db.Column(db.BigInteger, nullable=True, default=0)
    like_count = db.Column(db.BigInteger, nullable=True, default=0)
    comment_count = db.Column(db.BigInteger, nullable=True, default=0)
    thumbnail_url = db.Column(db.Text, nullable=True)
    transcript_text = db.Column(db.Text, nullable=True)
    transcript_source = db.Column(db.String(20), nullable=True)     # 'youtube_api' | 'whisper' | 'failed'
    transcript_language = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        db.UniqueConstraint("channel_fk_id", "video_id", name="uq_channel_video"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "video_id": self.video_id,
            "title": self.title,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "duration_seconds": self.duration_seconds or 0,
            "view_count": self.view_count or 0,
            "like_count": self.like_count or 0,
            "comment_count": self.comment_count or 0,
            "thumbnail_url": self.thumbnail_url,
            "transcript_source": self.transcript_source,
        }

    def __repr__(self):
        return f"<YTChannelVideo id={self.id} video_id={self.video_id}>"


class YTChannelAnalysisRun(db.Model):
    """
    Stores each analysis run result. Multiple runs can exist per channel.
    Preserves history like analytics_snapshots.
    """
    __tablename__ = "yt_channel_analysis_runs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel_fk_id = db.Column(db.Integer, db.ForeignKey("yt_analyzed_channels.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending | processing | completed | failed
    videos_analyzed_count = db.Column(db.Integer, nullable=True, default=0)
    analysis_summary = db.Column(db.JSON, nullable=True)            # insights, patterns, clusters, gaps, optimal_duration
    generated_ideas = db.Column(db.JSON, nullable=True)             # array of {title, hook, rationale}
    script_outline = db.Column(db.Text, nullable=True)              # full script for top idea
    error_message = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    @classmethod
    def get_by_user(cls, user_id: int, limit: int = 20):
        return (
            cls.query.filter_by(user_id=user_id)
            .order_by(cls.created_at.desc())
            .limit(limit)
            .all()
        )

    def to_dict(self):
        analysis_summary = self.analysis_summary
        if isinstance(analysis_summary, str):
            try:
                analysis_summary = json.loads(analysis_summary)
            except Exception:
                pass

        generated_ideas = self.generated_ideas
        if isinstance(generated_ideas, str):
            try:
                generated_ideas = json.loads(generated_ideas)
            except Exception:
                pass

        return {
            "id": self.id,
            "user_id": self.user_id,
            "channel_fk_id": self.channel_fk_id,
            "status": self.status,
            "videos_analyzed_count": self.videos_analyzed_count or 0,
            "analysis_summary": analysis_summary,
            "generated_ideas": generated_ideas,
            "script_outline": self.script_outline,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<YTChannelAnalysisRun id={self.id} status={self.status}>"
