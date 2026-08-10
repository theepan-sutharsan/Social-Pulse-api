"""
Social Pulse API — YouTube Channel Analysis Controller
Orchestrates channel resolution, video fetch, transcript batch fetch,
AI analysis (Claude or Gemini), DB persistence, and history retrieval.
All analysis runs synchronously within the Flask request (no Celery).
"""
import logging
from datetime import datetime, timezone
from flask import jsonify, request
from flask_jwt_extended import get_current_user
from app.extensions import db
from app.models.yt_channel_analysis_model import (
    YTAnalyzedChannel, YTChannelVideo, YTChannelAnalysisRun
)
from app.services.yt_channel_service import (
    resolve_channel, fetch_last_n_videos, YouTubeChannelServiceError
)
from app.services.yt_transcript_service import batch_get_transcripts
from app.services.yt_analysis_service import (
    build_analysis_payload, generate_channel_analysis, YTAnalysisServiceError
)

logger = logging.getLogger(__name__)


def start_analysis():
    """
    POST /api/yt-channel-analysis/start
    Payload: {
      "channel_url": "https://youtube.com/@handle",
      "video_count": 10 | 20 | 30 | 50  (default: 50)
    }

    Synchronously:
    1. Resolves channel via YouTube Data API
    2. Fetches last N video metadata (user-chosen count)
    3. Fetches/caches transcripts for all videos
    4. Calls Gemini first, with automatic fallback to another configured provider
    5. Persists results to DB
    6. Returns full analysis result
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized user."}), 401

    data = request.get_json(silent=True) or {}
    channel_url = (data.get("channel_url") or "").strip()
    if not channel_url:
        return jsonify({"error": "channel_url is required."}), 400

    provider = (data.get("provider") or "gemini").lower().strip()
    if provider not in ("claude", "gemini"):
        return jsonify({"error": f"Unsupported provider '{provider}'. Choose 'claude' or 'gemini'."}), 400

    # Validate video count — allowed: 10, 20, 30, 50
    ALLOWED_COUNTS = {10, 20, 30, 50}
    try:
        video_count = int(data.get("video_count") or 50)
    except (TypeError, ValueError):
        video_count = 50
    if video_count not in ALLOWED_COUNTS:
        # Clamp to nearest allowed value
        video_count = min(ALLOWED_COUNTS, key=lambda x: abs(x - video_count))

    # --- Step 1: Resolve channel ---
    try:
        channel_meta = resolve_channel(channel_url)
    except YouTubeChannelServiceError as e:
        return jsonify({"error": str(e)}), 400

    # Upsert channel record for this user
    channel_row = YTAnalyzedChannel.query.filter_by(
        user_id=user.id, channel_id=channel_meta["channel_id"]
    ).first()

    if not channel_row:
        channel_row = YTAnalyzedChannel(
            user_id=user.id,
            channel_id=channel_meta["channel_id"],
            channel_title=channel_meta["channel_title"],
            channel_handle=channel_meta["channel_handle"],
            subscriber_count=channel_meta["subscriber_count"],
            thumbnail_url=channel_meta["thumbnail_url"],
        )
        db.session.add(channel_row)
    else:
        # Update stale metadata
        channel_row.channel_title = channel_meta["channel_title"]
        channel_row.channel_handle = channel_meta["channel_handle"]
        channel_row.subscriber_count = channel_meta["subscriber_count"]
        channel_row.thumbnail_url = channel_meta["thumbnail_url"]

    db.session.flush()  # get channel_row.id before inserting run

    # Create analysis run record (status=processing)
    run = YTChannelAnalysisRun(
        user_id=user.id,
        channel_fk_id=channel_row.id,
        status="processing",
        started_at=datetime.now(timezone.utc),
    )
    db.session.add(run)
    db.session.commit()

    try:
        # --- Step 2: Fetch last N videos (user-selected count) ---
        try:
            videos = fetch_last_n_videos(channel_meta["channel_id"], n=video_count)
        except YouTubeChannelServiceError as e:
            raise Exception(f"Video fetch failed: {e}")

        # Upsert video records (cache)
        for v in videos:
            existing = YTChannelVideo.query.filter_by(
                channel_fk_id=channel_row.id, video_id=v["video_id"]
            ).first()
            if not existing:
                db.session.add(YTChannelVideo(
                    channel_fk_id=channel_row.id,
                    video_id=v["video_id"],
                    title=v["title"],
                    description=v["description"][:2000] if v.get("description") else None,
                    tags_json=v.get("tags", []),
                    published_at=v.get("published_at"),
                    duration_seconds=v.get("duration_seconds", 0),
                    view_count=v.get("view_count", 0),
                    like_count=v.get("like_count", 0),
                    comment_count=v.get("comment_count", 0),
                    thumbnail_url=v.get("thumbnail_url"),
                ))
        db.session.commit()

        # --- Step 3: Batch fetch transcripts ---
        # Check which videos already have cached transcripts in the DB
        video_ids = [v["video_id"] for v in videos]
        existing_rows = {
            row.video_id: row
            for row in YTChannelVideo.query.filter(
                YTChannelVideo.channel_fk_id == channel_row.id,
                YTChannelVideo.video_id.in_(video_ids),
            ).all()
        }

        uncached_ids = [
            vid for vid in video_ids
            if not existing_rows.get(vid) or not existing_rows[vid].transcript_text
        ]

        # Only fetch transcripts not already cached
        fetched_transcripts: dict[str, dict] = {}
        if uncached_ids:
            fetched_transcripts = batch_get_transcripts(uncached_ids, max_whisper_fallbacks=5)
            # Update DB with newly fetched transcripts
            for vid_id, t_result in fetched_transcripts.items():
                row = existing_rows.get(vid_id)
                if row:
                    row.transcript_text = t_result.get("text")
                    row.transcript_source = t_result.get("source")
                    row.transcript_language = t_result.get("language")
            db.session.commit()

        # Build complete transcript map (cached + freshly fetched)
        all_transcripts: dict[str, dict] = {}
        for vid_id in video_ids:
            row = existing_rows.get(vid_id)
            if row and row.transcript_text:
                all_transcripts[vid_id] = {
                    "text": row.transcript_text,
                    "source": row.transcript_source or "cache",
                    "language": row.transcript_language,
                }
            elif vid_id in fetched_transcripts:
                all_transcripts[vid_id] = fetched_transcripts[vid_id]
            else:
                all_transcripts[vid_id] = {"text": None, "source": "failed", "language": None}

        # --- Step 4: Build payload + call AI provider ---
        try:
            payload = build_analysis_payload(videos, all_transcripts)
            analysis_result, provider_used = generate_channel_analysis(
                channel_meta["channel_title"], payload, provider=provider
            )
        except YTAnalysisServiceError as e:
            raise Exception(f"AI analysis failed: {e}")

        # --- Step 5: Persist results ---
        run.status = "completed"
        run.videos_analyzed_count = len(videos)
        suggestions = analysis_result.get("top_5_content_suggestions", [])
        if not suggestions:
            # Fallback if AI put future_video_ideas as simple strings
            future_ideas = analysis_result.get("overall_channel_insights", {}).get("future_video_ideas", [])
            suggestions = [
                {"title": str(idea), "hook": "High-CTR hook based on channel data", "rationale": "Recommended content direction"}
                for idea in future_ideas
            ]

        script_outline = analysis_result.get("top_pick_script_outline", "")

        run.analysis_summary = {
            "video_analysis": analysis_result.get("video_analysis", []),
            "overall_channel_insights": analysis_result.get("overall_channel_insights", {}),
            "top_5_content_suggestions": suggestions,
            "top_pick_script_outline": script_outline,
            "total_videos_analyzed": analysis_result.get("total_videos_analyzed", len(videos)),
            # Metadata
            "ai_provider": provider_used,
            "video_count_requested": video_count,
        }
        run.generated_ideas = suggestions
        run.script_outline = script_outline
        run.completed_at = datetime.now(timezone.utc)
        channel_row.last_analyzed_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            "message": "Channel analysis completed successfully.",
            "run": run.to_dict(),
            "channel": channel_row.to_dict(),
        }), 201

    except Exception as e:
        logger.error(f"Channel analysis failed: {e}")
        run.status = "failed"
        run.error_message = str(e)
        db.session.commit()
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


def get_analysis_run(run_id: int):
    """
    GET /api/yt-channel-analysis/<run_id>
    Returns the full analysis result for a specific run.
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized user."}), 401

    run = YTChannelAnalysisRun.query.get(run_id)
    if not run:
        return jsonify({"error": "Analysis run not found."}), 404

    if user.role != "admin" and run.user_id != user.id:
        return jsonify({"error": "Forbidden. Access denied."}), 403

    channel = YTAnalyzedChannel.query.get(run.channel_fk_id)
    return jsonify({
        "run": run.to_dict(),
        "channel": channel.to_dict() if channel else None,
    }), 200


def get_analysis_history():
    """
    GET /api/yt-channel-analysis/history
    Returns the last 20 analysis runs for the current user.
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized user."}), 401

    runs = YTChannelAnalysisRun.get_by_user(user.id, limit=20)

    results = []
    for run in runs:
        channel = YTAnalyzedChannel.query.get(run.channel_fk_id)
        results.append({
            **run.to_dict(),
            "channel": channel.to_dict() if channel else None,
        })

    return jsonify({"count": len(results), "history": results}), 200
