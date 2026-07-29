"""
Social Pulse API — Channel Analytics Engine
Calculates channel-level metrics:
- Average Views / Likes / Comments per video
- Subscriber-to-View Ratio & Views Per Subscriber
- Upload Frequency (Videos per week / month)
- Scores: Activity, Consistency, Engagement, Popularity, Growth, Overall Channel Score (0-100)
"""


def calculate_channel_analytics(channel_dict: dict, videos: list) -> dict:
    subscribers = max(1, channel_dict.get("subscriber_count") or channel_dict.get("subscribers") or 0)
    total_views = max(0, channel_dict.get("total_views") or 0)
    total_videos = max(len(videos), channel_dict.get("video_count") or channel_dict.get("total_videos_count") or 0)

    if videos:
        avg_views = round(sum(v.get("views", 0) for v in videos) / max(len(videos), 1), 2)
        avg_likes = round(sum(v.get("likes", 0) for v in videos) / max(len(videos), 1), 2)
        avg_comments = round(sum(v.get("comments", 0) for v in videos) / max(len(videos), 1), 2)
    else:
        avg_views = round(total_views / max(total_videos, 1), 2)
        avg_likes = 0.0
        avg_comments = 0.0

    sub_to_view_ratio = round((subscribers / max(total_views, 1)) * 100, 4)
    views_per_subscriber = round(total_views / max(subscribers, 1), 2)

    videos_per_week = round(len(videos) / 4.0, 2) if videos else 1.0
    videos_per_month = round(len(videos) / 1.0, 2) if videos else 4.0

    activity_score = min(100.0, round((videos_per_month / 8.0) * 100.0, 1))
    consistency_score = min(100.0, round((videos_per_week / 2.0) * 100.0, 1))
    
    eng_rate = ((avg_likes + avg_comments) / max(avg_views, 1)) * 100
    engagement_score = min(100.0, round((eng_rate / 5.0) * 100.0, 1))
    popularity_score = min(100.0, round((subscribers / 100000.0) * 100.0, 1))
    growth_score = min(100.0, round((avg_views / 10000.0) * 100.0, 1))

    overall_score = round(
        (activity_score * 0.15) +
        (consistency_score * 0.20) +
        (engagement_score * 0.30) +
        (popularity_score * 0.15) +
        (growth_score * 0.20),
        1
    )

    grade = "A+" if overall_score >= 85 else ("A" if overall_score >= 75 else ("B+" if overall_score >= 65 else ("B" if overall_score >= 50 else "C")))

    return {
        "channel_grade": grade,
        "overall_channel_score": overall_score,
        "averages": {
            "average_views_per_video": avg_views,
            "average_likes_per_video": avg_likes,
            "average_comments_per_video": avg_comments,
        },
        "ratios": {
            "subscriber_to_view_ratio": sub_to_view_ratio,
            "views_per_subscriber": views_per_subscriber,
        },
        "upload_frequency": {
            "videos_per_week": videos_per_week,
            "videos_per_month": videos_per_month,
        },
        "scores": {
            "activity_score": activity_score,
            "consistency_score": consistency_score,
            "engagement_score": engagement_score,
            "popularity_score": popularity_score,
            "growth_score": growth_score,
            "overall_score": overall_score,
        }
    }
