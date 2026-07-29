"""
Social Pulse API — Viral Score Engine
Calculates a 0-100 Viral Score based on view velocity, like velocity, comment velocity, engagement rate, and upload age.
"""
from datetime import datetime


def calculate_viral_score(video_dict: dict, metrics_dict: dict = None) -> dict:
    views = max(0, (metrics_dict or {}).get("views") or video_dict.get("views") or 0)
    likes = max(0, (metrics_dict or {}).get("likes") or video_dict.get("likes") or 0)
    comments = max(0, (metrics_dict or {}).get("comments") or video_dict.get("comments") or 0)
    
    pub_at = video_dict.get("published_at")
    hours_since_pub = 24.0
    if pub_at:
        try:
            if isinstance(pub_at, str):
                dt = datetime.fromisoformat(pub_at.replace("Z", "+00:00")).replace(tzinfo=None)
            else:
                dt = pub_at
            delta = (datetime.utcnow() - dt).total_seconds()
            hours_since_pub = max(1.0, delta / 3600.0)
        except Exception:
            hours_since_pub = 24.0

    views_per_hour = round(views / hours_since_pub, 2)
    likes_per_hour = round(likes / hours_since_pub, 2)
    comments_per_hour = round(comments / hours_since_pub, 2)

    engagement_rate = round(((likes + comments) / max(views, 1)) * 100, 2)

    v_score = min(40.0, (views_per_hour / 500.0) * 40.0)
    l_score = min(30.0, ((likes_per_hour + comments_per_hour * 2) / 50.0) * 30.0)
    e_score = min(20.0, (engagement_rate / 10.0) * 20.0)
    r_score = max(0.0, 10.0 - (hours_since_pub / 24.0) * 2.0)

    viral_score = min(100.0, round(v_score + l_score + e_score + r_score, 1))
    level = "Mega Viral" if viral_score >= 80 else ("High Viral" if viral_score >= 60 else ("Moderate Viral" if viral_score >= 40 else "Standard"))

    return {
        "viral_score": viral_score,
        "viral_level": level,
        "metrics": {
            "views_per_hour": views_per_hour,
            "likes_per_hour": likes_per_hour,
            "comments_per_hour": comments_per_hour,
            "views_per_minute": round(views_per_hour / 60.0, 2),
            "engagement_rate": engagement_rate,
            "upload_age_hours": round(hours_since_pub, 1),
        },
        "breakdown": {
            "view_velocity_score": round(v_score, 1),
            "interaction_velocity_score": round(l_score, 1),
            "engagement_score": round(e_score, 1),
            "recency_boost": round(r_score, 1),
        }
    }
