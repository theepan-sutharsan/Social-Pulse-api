"""
Social Pulse API — Video Analytics Controller
Handles video historical tracking, detailed video metrics, SEO analysis, view predictions, and viral score calculation.
"""
from flask import jsonify, request
from app.models.video_model import Video
from app.models.video_history_model import VideoHistory
from app.services import viral_score_engine, seo_engine, prediction_engine


def get_video_history(video_id: int):
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found."}), 404

    history_records = VideoHistory.get_history_for_video(video.id)
    return jsonify({
        "video_id": video.id,
        "external_id": video.external_id,
        "count": len(history_records),
        "history": [h.to_dict() for h in history_records],
    }), 200


def get_video_analytics(video_id: int):
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found."}), 404

    v_dict = video.to_dict()
    viral_info = viral_score_engine.calculate_viral_score(v_dict)

    views = v_dict.get("views", 0)
    likes = v_dict.get("likes", 0)
    comments = v_dict.get("comments", 0)
    shares = v_dict.get("shares", 0)

    like_ratio = round(likes / max(views, 1), 4)
    comment_ratio = round(comments / max(views, 1), 4)
    engagement_rate = round((likes + comments + shares) / max(views, 1) * 100, 2)

    return jsonify({
        "video": v_dict,
        "metrics": {
            "views": views,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "engagement_rate": engagement_rate,
            "like_ratio": like_ratio,
            "comment_ratio": comment_ratio,
            "views_per_hour": viral_info["metrics"]["views_per_hour"],
            "views_per_minute": viral_info["metrics"]["views_per_minute"],
            "viral_score": viral_info["viral_score"],
            "viral_level": viral_info["viral_level"],
        }
    }), 200


def get_video_seo(video_id: int):
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found."}), 404

    v_dict = video.to_dict()
    seo_analysis = seo_engine.analyze_video_seo(v_dict)
    return jsonify({
        "video_id": video.id,
        "seo": seo_analysis,
    }), 200


def get_video_prediction(video_id: int):
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found."}), 404

    history = VideoHistory.get_history_for_video(video.id)
    current_views = video.to_dict().get("views", 0)

    pred = prediction_engine.predict_view_growth(history, current_views)
    return jsonify({
        "video_id": video.id,
        "prediction": pred,
    }), 200


def get_video_viral_score(video_id: int):
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found."}), 404

    v_dict = video.to_dict()
    viral_info = viral_score_engine.calculate_viral_score(v_dict)
    return jsonify({
        "video_id": video.id,
        "viral_analysis": viral_info,
    }), 200
