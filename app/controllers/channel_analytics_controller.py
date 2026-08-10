"""
Social Pulse API — Channel Analytics Controller
Handles SocialBlade-style channel statistics, historical tracking, growth metrics, revenue estimation, predictions, and top videos.
"""
from flask import jsonify, request
from flask_jwt_extended import get_current_user
from app.models.tracked_channel_model import TrackedChannel
from app.models.connected_account_model import ConnectedAccount
from app.models.channel_history_model import ChannelHistory
from app.models.video_model import Video
from app.integrations import youtube_client
from app.services import growth_engine, revenue_engine, prediction_engine, channel_analytics_engine


def _resolve_channel(channel_identifier):
    # 1. Check if ID is integer DB primary key
    if str(channel_identifier).isdigit():
        tc = TrackedChannel.query.get(int(channel_identifier))
        if tc:
            return tc
        ca = ConnectedAccount.query.get(int(channel_identifier))
        if ca and ca.platform == "youtube":
            return ca

    # 2. Check by string channel_id
    tc = TrackedChannel.get_by_channel_id(str(channel_identifier))
    if tc:
        return tc

    # 3. Handle / URL resolution via youtube_client
    info = youtube_client.get_channel_info(str(channel_identifier))
    if info and info.get("channel_id"):
        tc = TrackedChannel.get_by_channel_id(info["channel_id"])
        if tc:
            return tc

    return info


def get_channel_detail(channel_id):
    ch = _resolve_channel(channel_id)
    if not ch:
        return jsonify({"error": "Channel not found."}), 404

    if isinstance(ch, TrackedChannel):
        ch_dict = ch.to_dict()
        videos = [v.to_dict() for v in ch.videos]
        history = ChannelHistory.get_history_for_channel(ch.channel_id)
    elif isinstance(ch, ConnectedAccount):
        ch_dict = {
            "id": ch.id,
            "channel_id": ch.platform_account_id,
            "channel_name": ch.display_name,
            "platform": ch.platform,
            "subscriber_count": 0,
            "total_views": 0,
            "video_count": len(ch.videos),
        }
        videos = [v.to_dict() for v in ch.videos]
        history = []
    else:
        ch_dict = {
            "id": None,
            "channel_id": ch.get("channel_id"),
            "channel_name": ch.get("display_name"),
            "subscriber_count": ch.get("subscriber_count", 0),
            "total_views": ch.get("total_views", 0),
            "video_count": ch.get("video_count", 0),
            "profile_image": ch.get("thumbnail"),
            "banner_url": ch.get("banner_url"),
            "data_source": ch.get("data_source", "youtube_api"),
        }
        videos = [v for v in youtube_client.get_channel_videos(ch.get("channel_id"), max_results=50)]
        history = []

    analytics = channel_analytics_engine.calculate_channel_analytics(ch_dict, videos)
    return jsonify({
        "channel": ch_dict,
        "analytics": analytics,
    }), 200


def get_channel_history(channel_id):
    ch = _resolve_channel(channel_id)
    if isinstance(ch, TrackedChannel):
        target_id = ch.channel_id
    elif isinstance(ch, ConnectedAccount):
        target_id = ch.platform_account_id
    elif isinstance(ch, dict):
        target_id = ch.get("channel_id")
    else:
        target_id = str(channel_id)

    history_records = ChannelHistory.get_history_for_channel(target_id)
    return jsonify({
        "channel_id": target_id,
        "count": len(history_records),
        "history": [h.to_dict() for h in history_records],
    }), 200


def get_channel_growth(channel_id):
    ch = _resolve_channel(channel_id)
    if not ch:
        return jsonify({"error": "Channel not found."}), 404

    if isinstance(ch, TrackedChannel):
        ch_dict = ch.to_dict()
        history = ChannelHistory.get_history_for_channel(ch.channel_id)
    elif isinstance(ch, ConnectedAccount):
        ch_dict = {"channel_id": ch.platform_account_id, "subscriber_count": 0, "total_views": 0, "video_count": len(ch.videos)}
        history = []
    else:
        ch_dict = ch
        history = []

    growth = growth_engine.calculate_growth_metrics(history, ch_dict)
    return jsonify({
        "channel_id": ch_dict.get("channel_id"),
        "growth": growth,
    }), 200


def get_channel_revenue(channel_id):
    ch = _resolve_channel(channel_id)
    if not ch:
        return jsonify({"error": "Channel not found."}), 404

    low_cpm = request.args.get("low_cpm", default=2.0, type=float)
    high_cpm = request.args.get("high_cpm", default=8.0, type=float)

    if isinstance(ch, TrackedChannel):
        ch_dict = ch.to_dict()
        history = ChannelHistory.get_history_for_channel(ch.channel_id)
    elif isinstance(ch, ConnectedAccount):
        ch_dict = {"channel_id": ch.platform_account_id, "subscriber_count": 0, "total_views": 0, "video_count": len(ch.videos)}
        history = []
    else:
        ch_dict = ch
        history = []

    growth = growth_engine.calculate_growth_metrics(history, ch_dict)
    monthly_views = growth.get("monthly_growth", {}).get("views") or (growth.get("average_daily_views", 0) * 30)
    total_views = ch_dict.get("total_views") or 0

    revenue = revenue_engine.calculate_estimated_revenue(
        monthly_views=monthly_views,
        total_lifetime_views=total_views,
        low_cpm=low_cpm,
        high_cpm=high_cpm,
    )

    return jsonify({
        "channel_id": ch_dict.get("channel_id"),
        "revenue_estimate": revenue,
    }), 200


def get_channel_predictions(channel_id):
    ch = _resolve_channel(channel_id)
    if not ch:
        return jsonify({"error": "Channel not found."}), 404

    if isinstance(ch, TrackedChannel):
        ch_dict = ch.to_dict()
        history = ChannelHistory.get_history_for_channel(ch.channel_id)
    elif isinstance(ch, ConnectedAccount):
        ch_dict = {"channel_id": ch.platform_account_id, "subscriber_count": 0, "total_views": 0, "video_count": len(ch.videos)}
        history = []
    else:
        ch_dict = ch
        history = []

    sub_pred = prediction_engine.predict_subscriber_growth(history, ch_dict.get("subscriber_count") or ch_dict.get("subscribers") or 0)
    view_pred = prediction_engine.predict_view_growth(history, ch_dict.get("total_views") or 0)

    return jsonify({
        "channel_id": ch_dict.get("channel_id"),
        "subscriber_predictions": sub_pred,
        "view_predictions": view_pred,
    }), 200


def get_channel_top_videos(channel_id):
    ch = _resolve_channel(channel_id)
    if not ch:
        return jsonify({"error": "Channel not found."}), 404

    sort_by = request.args.get("sort_by", default="views").lower()

    if isinstance(ch, TrackedChannel):
        videos = [v.to_dict() for v in ch.videos]
    elif isinstance(ch, ConnectedAccount):
        videos = [v.to_dict() for v in ch.videos]
    else:
        target_id = ch.get("channel_id") if isinstance(ch, dict) else str(channel_id)
        videos = youtube_client.get_channel_videos(target_id, max_results=50)

    if sort_by == "likes":
        top_vids = sorted(videos, key=lambda v: v.get("likes", 0), reverse=True)
    elif sort_by == "comments":
        top_vids = sorted(videos, key=lambda v: v.get("comments", 0), reverse=True)
    else:
        top_vids = sorted(videos, key=lambda v: v.get("views", 0), reverse=True)

    return jsonify({
        "channel_id": ch.channel_id if isinstance(ch, TrackedChannel) else (ch.platform_account_id if isinstance(ch, ConnectedAccount) else ch.get("channel_id")),
        "count": len(top_vids),
        "top_videos": top_vids[:20],
    }), 200
