"""
Social Pulse API — Suggestion Source Controller
Manages the many-to-many junction between suggestions and source videos.
This is the SIGNATURE relationship for the viva demonstration.
"""
from flask import jsonify
from flask_jwt_extended import get_current_user
from app.models.suggestion_model import Suggestion
from app.models.suggestion_source_model import SuggestionSource
from app.models.video_model import Video


def get_suggestion_sources(suggestion_id: int):
    """Get all source videos linked to a suggestion."""
    user = get_current_user()
    suggestion = Suggestion.query.get(suggestion_id)
    if not suggestion:
        return jsonify({"error": "Suggestion not found."}), 404
    if user.role != "admin" and suggestion.user_id != user.id:
        return jsonify({"error": "Forbidden."}), 403

    sources = SuggestionSource.query.filter_by(suggestion_id=suggestion_id).all()
    source_videos = []
    for src in sources:
        video = Video.query.get(src.video_id)
        if video:
            v_dict = video.to_dict_with_metrics()
            v_dict["source_id"] = src.id
            v_dict["source_created_at"] = src.created_at.isoformat() if src.created_at else None
            source_videos.append(v_dict)

    return jsonify({
        "suggestion_id": suggestion_id,
        "source_count": len(source_videos),
        "source_videos": source_videos,
    }), 200


def get_video_suggestions(video_id: int):
    """Get all suggestions that used a specific video as a source."""
    user = get_current_user()
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found."}), 404

    sources = SuggestionSource.query.filter_by(video_id=video_id).all()
    suggestions = []
    for src in sources:
        suggestion = Suggestion.query.get(src.suggestion_id)
        if suggestion and (user.role == "admin" or suggestion.user_id == user.id):
            s_dict = suggestion.to_dict()
            s_dict["source_link_id"] = src.id
            suggestions.append(s_dict)

    return jsonify({
        "video_id": video_id,
        "suggestions_count": len(suggestions),
        "suggestions": suggestions,
    }), 200
