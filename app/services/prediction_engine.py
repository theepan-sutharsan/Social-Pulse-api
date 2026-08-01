"""
Social Pulse API — Subscriber & View Prediction Engine
Predicts future channel subscribers and view milestones for 1 Day, 7 Days, 30 Days, 90 Days, and 1 Year.
"""
from datetime import datetime, timedelta


def predict_subscriber_growth(history_records: list, current_subs: int) -> dict:
    current_subs = max(0, current_subs or 0)
    daily_growth_rates = []
    if len(history_records) >= 2:
        for i in range(1, len(history_records)):
            prev = history_records[i-1].subscribers if hasattr(history_records[i-1], "subscribers") else history_records[i-1].get("subscribers", 0)
            curr = history_records[i].subscribers if hasattr(history_records[i], "subscribers") else history_records[i].get("subscribers", 0)
            diff = curr - prev
            if diff >= 0:
                daily_growth_rates.append(diff)

    avg_daily_rate = (sum(daily_growth_rates) / max(len(daily_growth_rates), 1)) if daily_growth_rates else (current_subs * 0.001)
    avg_daily_rate = max(1.0, avg_daily_rate)

    sample_size = len(daily_growth_rates)
    confidence = 92.5 if sample_size > 30 else (85.0 if sample_size > 7 else (72.0 if sample_size > 1 else 60.0))

    pred_1d = int(current_subs + avg_daily_rate)
    pred_7d = int(current_subs + avg_daily_rate * 7)
    pred_30d = int(current_subs + avg_daily_rate * 30)
    pred_90d = int(current_subs + avg_daily_rate * 90)
    pred_1y = int(current_subs + avg_daily_rate * 365)

    return {
        "current_subscribers": current_subs,
        "daily_growth_rate": round(avg_daily_rate, 2),
        "confidence_percentage": confidence,
        "predictions": {
            "tomorrow": {"days": 1, "predicted_subscribers": pred_1d, "gained": int(avg_daily_rate)},
            "in_7_days": {"days": 7, "predicted_subscribers": pred_7d, "gained": int(avg_daily_rate * 7)},
            "in_30_days": {"days": 30, "predicted_subscribers": pred_30d, "gained": int(avg_daily_rate * 30)},
            "in_90_days": {"days": 90, "predicted_subscribers": pred_90d, "gained": int(avg_daily_rate * 90)},
            "in_1_year": {"days": 365, "predicted_subscribers": pred_1y, "gained": int(avg_daily_rate * 365)},
        }
    }


def predict_view_growth(history_records: list, current_views: int) -> dict:
    current_views = max(0, current_views or 0)
    view_diffs = []
    if len(history_records) >= 2:
        for i in range(1, len(history_records)):
            prev = history_records[i-1].total_views if hasattr(history_records[i-1], "total_views") else history_records[i-1].get("total_views", 0)
            curr = history_records[i].total_views if hasattr(history_records[i], "total_views") else history_records[i].get("total_views", 0)
            diff = curr - prev
            if diff >= 0:
                view_diffs.append(diff)

    avg_daily_views = (sum(view_diffs) / max(len(view_diffs), 1)) if view_diffs else (current_views * 0.005)
    avg_daily_views = max(50.0, avg_daily_views)

    sample_size = len(view_diffs)
    confidence = 90.0 if sample_size > 30 else (80.0 if sample_size > 7 else 65.0)

    daily_views = int(avg_daily_views)
    weekly_views = int(avg_daily_views * 7)
    monthly_views = int(avg_daily_views * 30)
    yearly_views = int(avg_daily_views * 365)

    return {
        "current_total_views": current_views,
        "avg_daily_views": round(avg_daily_views, 2),
        "confidence_percentage": confidence,
        "predictions": {
            "daily_views": daily_views,
            "weekly_views": weekly_views,
            "monthly_views": monthly_views,
            "yearly_views": yearly_views,
            "expected_total_views_in_1y": current_views + yearly_views,
        }
    }
