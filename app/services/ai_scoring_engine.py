"""
Social Pulse API — AI Scoring Engine
Generates 0-100 scores for Profile, Growth, SEO, Engagement, Consistency, Content Quality, Audience Quality, Brand, Creator, and Overall Score.
"""


def calculate_ai_scores(account_dict: dict, posts: list = None, history_records: list = None) -> dict:
    """
    Computes comprehensive 0-100 AI quality and performance scores across dimensions.
    """
    followers = max(0, account_dict.get("subscriber_count") or account_dict.get("subscribers") or account_dict.get("followers") or 0)
    views = max(0, account_dict.get("total_views") or 0)
    posts = posts or []

    # 1. Profile Score (Bio, image, category, verification)
    has_bio = bool(account_dict.get("description") or account_dict.get("niche"))
    has_img = bool(account_dict.get("profile_image") or account_dict.get("banner_url"))
    profile_score = min(100.0, round((40.0 if has_bio else 10.0) + (40.0 if has_img else 10.0) + min(20.0, (followers / 5000.0) * 20.0), 1))

    # 2. Growth Score
    hist_count = len(history_records or [])
    growth_score = min(100.0, round(50.0 + min(50.0, hist_count * 2.0), 1))

    # 3. SEO Score
    if posts:
        titles_len = sum(len(p.get("title", "")) for p in posts) / max(len(posts), 1)
        has_tags = sum(1 for p in posts if p.get("tags"))
        seo_score = min(100.0, round(min(50.0, (titles_len / 40.0) * 50.0) + (has_tags / max(len(posts), 1)) * 50.0, 1))
    else:
        seo_score = 70.0

    # 4. Engagement Score
    if posts:
        tot_views = sum(p.get("views", 0) for p in posts)
        tot_interactions = sum((p.get("likes", 0) + p.get("comments", 0) + p.get("shares", 0)) for p in posts)
        eng_pct = (tot_interactions / max(tot_views, 1)) * 100
        engagement_score = min(100.0, round(min(100.0, eng_pct * 15.0), 1))
    else:
        engagement_score = 65.0

    # 5. Consistency Score
    post_cnt = len(posts)
    consistency_score = min(100.0, round(min(100.0, (post_cnt / 10.0) * 100.0), 1))

    # 6. Content Quality Score
    content_quality_score = round((seo_score * 0.4) + (engagement_score * 0.6), 1)

    # 7. Audience Quality Score
    audience_quality_score = min(100.0, round(min(100.0, (followers / 10000.0) * 50.0 + engagement_score * 0.5), 1))

    # 8. Brand Score
    brand_score = min(100.0, round((profile_score * 0.3) + (audience_quality_score * 0.4) + (consistency_score * 0.3), 1))

    # 9. Creator Score
    creator_score = round((engagement_score * 0.35) + (content_quality_score * 0.35) + (growth_score * 0.30), 1)

    # 10. Overall Score
    overall_score = round(
        (profile_score * 0.10) +
        (growth_score * 0.15) +
        (seo_score * 0.15) +
        (engagement_score * 0.25) +
        (consistency_score * 0.15) +
        (brand_score * 0.10) +
        (creator_score * 0.10),
        1
    )

    return {
        "overall_score": overall_score,
        "scores": {
            "profile_score": profile_score,
            "growth_score": growth_score,
            "seo_score": seo_score,
            "engagement_score": engagement_score,
            "consistency_score": consistency_score,
            "content_quality_score": content_quality_score,
            "audience_quality_score": audience_quality_score,
            "brand_score": brand_score,
            "creator_score": creator_score,
            "overall_score": overall_score,
        }
    }
