"""
Social Pulse API — Analytics Controller
Platform-level analytics and aggregations.
"""
from flask import jsonify, request
from flask_jwt_extended import get_current_user
from app.extensions import db
from app.models.connected_account_model import ConnectedAccount
from app.models.video_model import Video
from app.models.video_metric_model import VideoMetric
from sqlalchemy import func


def get_platform_breakdown():
    """Get video count and total views breakdown by platform."""
    user = get_current_user()
    if user.role == "admin":
        query = db.session.query(
            Video.platform,
            func.count(Video.id).label("video_count"),
        ).group_by(Video.platform)
    else:
        owned_ids = [a.id for a in ConnectedAccount.query.filter_by(user_id=user.id).all()]
        query = db.session.query(
            Video.platform,
            func.count(Video.id).label("video_count"),
        ).filter(
            Video.connected_account_id.in_(owned_ids)
        ).group_by(Video.platform)

    results = query.all()
    return jsonify({
        "platform_breakdown": [
            {"platform": r.platform, "video_count": r.video_count}
            for r in results
        ]
    }), 200


def get_top_videos():
    """Get top 10 videos by latest view count."""
    user = get_current_user()
    if user.role == "admin":
        video_ids = [v.id for v in Video.query.all()]
    else:
        owned_ids = [a.id for a in ConnectedAccount.query.filter_by(user_id=user.id).all()]
        video_ids = [
            v.id for v in Video.query.filter(Video.connected_account_id.in_(owned_ids)).all()
        ]

    top_videos = []
    for vid_id in video_ids:
        latest = (
            VideoMetric.query.filter_by(video_id=vid_id)
            .order_by(VideoMetric.recorded_at.desc())
            .first()
        )
        if latest:
            video = Video.query.get(vid_id)
            top_videos.append({
                **video.to_dict(),
                "latest_views": latest.views,
                "latest_engagement": latest.engagement_rate,
            })

    top_videos.sort(key=lambda x: x.get("latest_views", 0), reverse=True)
    return jsonify({"top_videos": top_videos[:10]}), 200


def get_engagement_trends():
    """Get average engagement rate over time for the user's connected accounts."""
    user = get_current_user()
    owned_ids = [a.id for a in ConnectedAccount.query.filter_by(user_id=user.id).all()]
    video_ids = [
        v.id for v in Video.query.filter(Video.connected_account_id.in_(owned_ids)).all()
    ]

    metrics = (
        VideoMetric.query
        .filter(VideoMetric.video_id.in_(video_ids))
        .order_by(VideoMetric.recorded_at.asc())
        .all()
    )

    # Group by date
    from collections import defaultdict
    by_date = defaultdict(list)
    for m in metrics:
        date_key = m.recorded_at.strftime("%Y-%m-%d") if m.recorded_at else "unknown"
        by_date[date_key].append(m.engagement_rate or 0)

    trends = [
        {"date": d, "avg_engagement": round(sum(rates) / len(rates), 4)}
        for d, rates in sorted(by_date.items())
    ]
    return jsonify({"engagement_trends": trends}), 200
