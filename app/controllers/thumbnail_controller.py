"""
Social Pulse API — Thumbnail Analysis Controller (stretch)
"""
from flask import jsonify, request
from flask_jwt_extended import get_current_user
from app.extensions import db
from app.models.video_model import Video
from app.models.thumbnail_analysis_model import ThumbnailAnalysis
from app.models.connected_account_model import ConnectedAccount
from app.utils import utc_now


def create_thumbnail_analysis(video_id: int):
    user = get_current_user()
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found."}), 404

    if user.role != "admin":
        owned_ids = [a.id for a in ConnectedAccount.query.filter_by(user_id=user.id).all()]
        if video.connected_account_id and video.connected_account_id not in owned_ids:
            return jsonify({"error": "Forbidden."}), 403

    existing = ThumbnailAnalysis.query.filter_by(video_id=video_id).first()
    if existing:
        return jsonify({"error": "Thumbnail analysis already exists for this video."}), 400

    # Stub analysis (real implementation would call vision AI)
    analysis = ThumbnailAnalysis(
        video_id=video_id,
        dominant_colors=["#FF6B35", "#004E98", "#FFFFFF"],
        has_text=True,
        face_count=1,
        composition_notes=(
            "Thumbnail features high-contrast colors with clear subject. "
            "Text overlay is readable. Face is centered with strong eye contact."
        ),
        score=0.82,
        created_at=utc_now(),
    )
    try:
        db.session.add(analysis)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

    return jsonify({"message": "Thumbnail analysis created.", "thumbnail_analysis": analysis.to_dict()}), 201


def get_thumbnail_analysis(video_id: int):
    user = get_current_user()
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found."}), 404

    if user.role != "admin":
        owned_ids = [a.id for a in ConnectedAccount.query.filter_by(user_id=user.id).all()]
        if video.connected_account_id and video.connected_account_id not in owned_ids:
            return jsonify({"error": "Forbidden."}), 403

    analysis = ThumbnailAnalysis.query.filter_by(video_id=video_id).first()
    if not analysis:
        return jsonify({"error": "Thumbnail analysis not found."}), 404

    return jsonify({"thumbnail_analysis": analysis.to_dict()}), 200
