"""
Social Pulse API — Video Analysis Controller
Handles video URL submission, orchestration of download/transcription/AI analysis, database persistence, and temporary file cleanup.
"""
import os
import shutil
import tempfile
from flask import jsonify, request
from flask_jwt_extended import get_current_user
from app.extensions import db
from app.models.video_analysis_model import VideoAnalysis
from app.services.video_downloader import (
    download_youtube_audio,
    VideoDownloadError,
)
from app.services.transcriber import (
    transcribe_audio,
    TranscriptionError,
)
from app.services.video_ai_analyzer import (
    analyze_video_content,
    analyze_video_thumbnail,
    AIAnalysisError,
)


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
    provider = (data.get("provider") or "auto").strip()

    if not youtube_url:
        return jsonify({"error": "youtube_url parameter is required."}), 400

    temp_dir = tempfile.mkdtemp(prefix="sp_yt_analysis_")
    audio_path = None

    try:
        # Step 1: Download Audio & Fetch Metadata
        try:
            audio_path, metadata = download_youtube_audio(youtube_url, temp_dir)
        except VideoDownloadError as e:
            return jsonify({"error": str(e)}), 400

        # Step 2: Transcribe Audio to Text
        try:
            transcript = transcribe_audio(audio_path)
        except TranscriptionError as e:
            return jsonify({"error": str(e)}), 422

        # Step 3: AI Content & Thumbnail Vision Analysis
        try:
            content_analysis = analyze_video_content(transcript, metadata.get("title", "Untitled Video"), provider=provider)
            thumbnail_analysis = analyze_video_thumbnail(metadata.get("thumbnail_url", ""), provider=provider)
        except AIAnalysisError as e:
            return jsonify({"error": str(e)}), 500

        overall_score = content_analysis.get("overall_score") or 8.0

        # Step 4: Database Persistence
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
        # Step 5: Temporary Audio File Cleanup
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


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
