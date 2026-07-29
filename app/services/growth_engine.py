"""
Social Pulse API — Growth Metrics Engine
Calculates daily, weekly, monthly, and yearly growth for subscribers/followers, views, and posts,
along with rolling averages (7d, 30d, 90d), growth velocity, and growth trends.
"""
from datetime import datetime


def calculate_growth_metrics(history_records: list, current_stats: dict = None) -> dict:
    if not history_records and not current_stats:
        return {
            "daily_subscriber_growth": 0,
            "daily_view_growth": 0,
            "daily_video_growth": 0,
            "weekly_growth": {"subscribers": 0, "views": 0, "videos": 0},
            "monthly_growth": {"subscribers": 0, "views": 0, "videos": 0},
            "yearly_growth": {"subscribers": 0, "views": 0, "videos": 0},
            "average_daily_views": 0,
            "average_daily_subscribers": 0,
            "growth_velocity": 0.0,
            "growth_trend": "stable",
            "growth_percentage": 0.0,
            "rolling_7d_avg_views": 0.0,
            "rolling_30d_avg_views": 0.0,
            "rolling_90d_avg_views": 0.0,
        }

    items = []
    for h in history_records:
        if hasattr(h, "to_dict"):
            items.append(h.to_dict())
        elif isinstance(h, dict):
            items.append(h)

    if current_stats and (not items or items[-1].get("date") != datetime.utcnow().strftime("%Y-%m-%d")):
        items.append({
            "subscribers": current_stats.get("subscriber_count") or current_stats.get("subscribers") or current_stats.get("followers") or 0,
            "total_views": current_stats.get("total_views") or 0,
            "total_videos": current_stats.get("video_count") or current_stats.get("total_videos") or current_stats.get("total_posts") or 0,
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
        })

    if len(items) < 2:
        latest = items[-1] if items else {}
        sub_cnt = latest.get("subscribers", 0)
        view_cnt = latest.get("total_views", 0)
        return {
            "daily_subscriber_growth": 0,
            "daily_view_growth": 0,
            "daily_video_growth": 0,
            "weekly_growth": {"subscribers": 0, "views": 0, "videos": 0},
            "monthly_growth": {"subscribers": 0, "views": 0, "videos": 0},
            "yearly_growth": {"subscribers": 0, "views": 0, "videos": 0},
            "average_daily_views": view_cnt,
            "average_daily_subscribers": sub_cnt,
            "growth_velocity": 1.0,
            "growth_trend": "stable",
            "growth_percentage": 0.0,
            "rolling_7d_avg_views": float(view_cnt),
            "rolling_30d_avg_views": float(view_cnt),
            "rolling_90d_avg_views": float(view_cnt),
        }

    latest = items[-1]
    yesterday = items[-2]

    daily_sub = latest.get("subscribers", 0) - yesterday.get("subscribers", 0)
    daily_view = latest.get("total_views", 0) - yesterday.get("total_views", 0)
    daily_video = latest.get("total_videos", 0) - yesterday.get("total_videos", 0)

    # Weekly
    w_idx = max(0, len(items) - 7)
    weekly_ref = items[w_idx]
    weekly_sub = latest.get("subscribers", 0) - weekly_ref.get("subscribers", 0)
    weekly_view = latest.get("total_views", 0) - weekly_ref.get("total_views", 0)
    weekly_video = latest.get("total_videos", 0) - weekly_ref.get("total_videos", 0)

    # Monthly
    m_idx = max(0, len(items) - 30)
    monthly_ref = items[m_idx]
    monthly_sub = latest.get("subscribers", 0) - monthly_ref.get("subscribers", 0)
    monthly_view = latest.get("total_views", 0) - monthly_ref.get("total_views", 0)
    monthly_video = latest.get("total_videos", 0) - monthly_ref.get("total_videos", 0)

    # Yearly
    y_idx = max(0, len(items) - 365)
    yearly_ref = items[y_idx]
    yearly_sub = latest.get("subscribers", 0) - yearly_ref.get("subscribers", 0)
    yearly_view = latest.get("total_views", 0) - yearly_ref.get("total_views", 0)
    yearly_video = latest.get("total_videos", 0) - yearly_ref.get("total_videos", 0)

    view_diffs = [max(0, items[i].get("total_views", 0) - items[i - 1].get("total_views", 0)) for i in range(1, len(items))]

    def avg_last(n):
        subset = view_diffs[-n:] if view_diffs else [0]
        return round(sum(subset) / max(len(subset), 1), 2)

    r7 = avg_last(7)
    r30 = avg_last(30)
    r90 = avg_last(90)

    initial_subs = items[0].get("subscribers", 1) or 1
    total_sub_diff = latest.get("subscribers", 0) - initial_subs
    growth_pct = round((total_sub_diff / initial_subs) * 100, 2)

    avg_sub_growth = sum(max(0, items[i].get("subscribers", 0) - items[i-1].get("subscribers", 0)) for i in range(1, len(items))) / max(len(items) - 1, 1)
    recent_sub_growth = sum(max(0, items[i].get("subscribers", 0) - items[i-1].get("subscribers", 0)) for i in range(max(1, len(items) - 7), len(items))) / max(min(7, len(items) - 1), 1)

    velocity = round(recent_sub_growth / max(avg_sub_growth, 0.1), 2)
    trend = "accelerating" if velocity > 1.2 else ("decelerating" if velocity < 0.8 else "stable")

    return {
        "daily_subscriber_growth": daily_sub,
        "daily_view_growth": daily_view,
        "daily_video_growth": daily_video,
        "weekly_growth": {"subscribers": weekly_sub, "views": weekly_view, "videos": weekly_video},
        "monthly_growth": {"subscribers": monthly_sub, "views": monthly_view, "videos": monthly_video},
        "yearly_growth": {"subscribers": yearly_sub, "views": yearly_view, "videos": yearly_video},
        "average_daily_views": r30,
        "average_daily_subscribers": round(avg_sub_growth, 2),
        "growth_velocity": velocity,
        "growth_trend": trend,
        "growth_percentage": growth_pct,
        "rolling_7d_avg_views": r7,
        "rolling_30d_avg_views": r30,
        "rolling_90d_avg_views": r90,
    }
