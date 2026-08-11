"""
Social Pulse API — Video Analysis Controller
Handles video URL submission, orchestration of transcript/transcription/AI analysis,
database persistence, and temporary file cleanup.
Transcript strategy: youtube-transcript-api (fast) → Whisper fallback (audio download).
"""
import os
import shutil
import tempfile
import logging
from flask import jsonify, request
from flask_jwt_extended import get_current_user
from app.extensions import db
from app.models.video_analysis_model import VideoAnalysis
from app.services.video_downloader import (
    download_youtube_audio,
    extract_video_id,
    VideoDownloadError,
)
from app.services.transcriber import (
    transcribe_audio,
    get_youtube_transcript,
    fetch_youtube_transcript_only,
    TranscriptionError,
    TranscriptFetchError,
)
from app.services.video_ai_analyzer import (
    analyze_video_content,
    analyze_video_thumbnail,
    AIAnalysisError,
)

logger = logging.getLogger(__name__)


def analyze_video():
    """
    POST /api/video-analysis/analyze
    Payload: { "youtube_url": "https://..." }
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized user."}), 401

    data = request.get_json(silent=True) or {}
    youtube_url = (data.get("youtube_url") or "").strip()
    if not youtube_url:
        return jsonify({"error": "youtube_url parameter is required."}), 400

    temp_dir = None
    audio_path = None
    transcript_source = "whisper"  # updated below if captions are found

    try:
        # ── Step 1: Fetch video metadata (needed for title, thumbnail, video ID) ──
        try:
            from app.services.video_downloader import get_video_metadata
            metadata = get_video_metadata(youtube_url)
        except VideoDownloadError as e:
            return jsonify({"error": str(e)}), 400

        video_id = metadata.get("id") or extract_video_id(youtube_url)

        # ── Step 2: Try youtube-transcript-api caption fetch (fast path) ──
        transcript = get_youtube_transcript(video_id)

        if transcript:
            logger.info(f"[VideoAnalysis] Caption transcript found for {video_id} — skipping audio download.")
            transcript_source = "youtube_captions"
        else:
            # ── Step 2b: Fallback — download audio + run Whisper ──
            logger.info(f"[VideoAnalysis] No caption transcript for {video_id} — falling back to Whisper.")
            try:
                temp_dir = tempfile.mkdtemp(prefix="sp_yt_analysis_")
                audio_path, _ = download_youtube_audio(youtube_url, temp_dir)
            except VideoDownloadError as e:
                return jsonify({"error": str(e)}), 400

            try:
                transcript = transcribe_audio(audio_path)
                transcript_source = "whisper"
            except TranscriptionError as e:
                return jsonify({"error": str(e)}), 422

        # ── Step 3: AI Content & Thumbnail Vision Analysis ──
        try:
            content_analysis = analyze_video_content(transcript, metadata.get("title", "Untitled Video"))
            thumbnail_analysis = analyze_video_thumbnail(metadata.get("thumbnail_url", ""))
        except AIAnalysisError as e:
            return jsonify({"error": str(e)}), 500

        # Attach transcript source metadata into the analysis JSON
        content_analysis["transcript_source"] = transcript_source

        overall_score = content_analysis.get("overall_score") or 8.0

        # ── Step 4: Database Persistence ──
        video_analysis = VideoAnalysis(
            user_id=user.id,
            youtube_url=youtube_url,
            video_title=metadata.get("title", "Untitled Video"),
            transcript=transcript,
            analysis_json=content_analysis,
            thumbnail_analysis_json=thumbnail_analysis,
            overall_score=float(overall_score),
        )

        db.session.add(video_analysis)
        db.session.commit()

        return jsonify({
            "message": "Video analysis completed successfully.",
            "analysis": video_analysis.to_dict(),
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"An error occurred during video analysis: {str(e)}"}), 500

    finally:
        # ── Step 5: Temporary Audio File Cleanup (only if Whisper path was used) ──
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


def get_transcript():
    """
    POST /api/video-analysis/transcript
    Fetches YouTube captions only using youtube-transcript-api.

    Unlike the full analysis endpoint, this route never downloads audio and
    never falls back to Whisper.  It is intended for the Video Transcript tab.
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized user."}), 401

    data = request.get_json(silent=True) or {}
    youtube_url = (data.get("youtube_url") or "").strip()
    if not youtube_url:
        return jsonify({"error": "youtube_url parameter is required."}), 400

    video_id = extract_video_id(youtube_url)
    if not video_id:
        return jsonify({"error": "Please enter a valid YouTube video URL."}), 400

    try:
        result = fetch_youtube_transcript_only(video_id)
    except TranscriptFetchError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:
        logger.exception("Unexpected transcript-only error for %s", video_id)
        return jsonify({"error": "Unable to fetch the YouTube transcript."}), 500

    return jsonify({
        "transcript": {
            "video_id": video_id,
            "transcript": result["text"],
            "language": result.get("language"),
            "source": "youtube_transcript_api",
            "segments": result.get("segments", []),
        }
    }), 200


def get_history():
    """
    GET /api/video-analysis/history
    Retrieves past analyses for the logged-in user.
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized user."}), 401

    analyses = VideoAnalysis.get_by_user(user.id, limit=50)
    return jsonify({
        "count": len(analyses),
        "history": [a.to_dict() for a in analyses],
    }), 200


def get_analysis_detail(analysis_id: int):
    """
    GET /api/video-analysis/<int:analysis_id>
    Retrieves details of a single analysis.
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized user."}), 401

    analysis = VideoAnalysis.query.get(analysis_id)
    if not analysis:
        return jsonify({"error": "Video analysis not found."}), 404

    if user.role != "admin" and analysis.user_id != user.id:
        return jsonify({"error": "Forbidden. Access denied."}), 403

    return jsonify({
        "analysis": analysis.to_dict(),
    }), 200


def delete_analysis(analysis_id: int):
    """
    DELETE /api/video-analysis/<int:analysis_id>
    Deletes a saved analysis owned by the logged-in user.
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized user."}), 401

    analysis = VideoAnalysis.query.get(analysis_id)
    if not analysis:
        return jsonify({"error": "Video analysis not found."}), 404

    if user.role != "admin" and analysis.user_id != user.id:
        return jsonify({"error": "Forbidden. Access denied."}), 403

    try:
        db.session.delete(analysis)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to delete video analysis %s", analysis_id)
        return jsonify({"error": f"Delete failed: {str(exc)}"}), 500

    return jsonify({"message": "Video analysis deleted."}), 200
