"""
Social Pulse API — Competitor Comparison Engine
Generates side-by-side comparative analysis (Followers, Growth, Engagement, Reach, Revenue, Scores)
between user accounts/channels and competitors.
"""
from app.services.growth_engine import calculate_growth_metrics
from app.services.revenue_engine import calculate_multiplatform_revenue
from app.services.ai_scoring_engine import calculate_ai_scores


def compare_user_vs_competitor(user_account_dict: dict, user_posts: list, competitor_account_dict: dict, competitor_posts: list) -> dict:
    """
    Computes comparative analytics, winner badges, and gap metrics for user vs competitor.
    """
    # User calculations
    u_subs = max(0, user_account_dict.get("subscriber_count") or user_account_dict.get("subscribers") or user_account_dict.get("followers") or 0)
    c_subs = max(0, competitor_account_dict.get("subscriber_count") or competitor_account_dict.get("subscribers") or competitor_account_dict.get("followers") or 0)

    u_views = max(0, user_account_dict.get("total_views") or 0)
    c_views = max(0, competitor_account_dict.get("total_views") or 0)

    u_scores = calculate_ai_scores(user_account_dict, user_posts)
    c_scores = calculate_ai_scores(competitor_account_dict, competitor_posts)

    u_rev = calculate_multiplatform_revenue(user_account_dict.get("platform", "youtube"), u_subs, u_views)
    c_rev = calculate_multiplatform_revenue(competitor_account_dict.get("platform", "youtube"), c_subs, c_views)

    sub_diff = u_subs - c_subs
    views_diff = u_views - c_views
    score_diff = round(u_scores["overall_score"] - c_scores["overall_score"], 1)

    return {
        "comparison": {
            "user": {
                "name": user_account_dict.get("display_name") or user_account_dict.get("channel_name") or "User Account",
                "platform": user_account_dict.get("platform", "youtube"),
                "followers": u_subs,
                "total_views": u_views,
                "post_count": len(user_posts),
                "overall_score": u_scores["overall_score"],
                "engagement_score": u_scores["scores"]["engagement_score"],
                "revenue_estimate": u_rev.get("monthly") or u_rev.get("creator_fund_monthly") or u_rev.get("sponsored_post"),
            },
            "competitor": {
                "name": competitor_account_dict.get("display_name") or competitor_account_dict.get("channel_name") or "Competitor Account",
                "platform": competitor_account_dict.get("platform", "youtube"),
                "followers": c_subs,
                "total_views": c_views,
                "post_count": len(competitor_posts),
                "overall_score": c_scores["overall_score"],
                "engagement_score": c_scores["scores"]["engagement_score"],
                "revenue_estimate": c_rev.get("monthly") or c_rev.get("creator_fund_monthly") or c_rev.get("sponsored_post"),
            },
        },
        "gaps": {
            "follower_gap": sub_diff,
            "views_gap": views_diff,
            "score_gap": score_diff,
            "leader": "User" if sub_diff >= 0 else "Competitor",
        },
        "highlights": [
            f"Follower lead: {'User is ahead by ' + str(abs(sub_diff)) if sub_diff >= 0 else 'Competitor leads by ' + str(abs(sub_diff)) + ' followers'}.",
            f"Score comparison: User ({u_scores['overall_score']}/100) vs Competitor ({c_scores['overall_score']}/100).",
        ]
    }
