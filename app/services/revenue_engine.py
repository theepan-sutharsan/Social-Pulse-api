"""
Social Pulse API — Multi-Platform Revenue & Sponsorship Estimation Engine
Generates revenue and sponsorship value estimates across YouTube, Instagram, Facebook, TikTok, X, and LinkedIn.
Always labels estimates as estimates (never claims official earnings).
"""


def calculate_estimated_revenue(monthly_views: int, total_lifetime_views: int = 0, low_cpm: float = 2.0, high_cpm: float = 8.0) -> dict:
    """
    YouTube CPM Revenue Calculator
    """
    monthly_views = max(0, int(monthly_views or 0))
    total_lifetime_views = max(monthly_views, int(total_lifetime_views or 0))

    daily_views_est = round(monthly_views / 30.0, 2)
    yearly_views_est = monthly_views * 12

    daily_min = round((daily_views_est / 1000.0) * low_cpm, 2)
    daily_max = round((daily_views_est / 1000.0) * high_cpm, 2)

    monthly_min = round((monthly_views / 1000.0) * low_cpm, 2)
    monthly_max = round((monthly_views / 1000.0) * high_cpm, 2)

    yearly_min = round((yearly_views_est / 1000.0) * low_cpm, 2)
    yearly_max = round((yearly_views_est / 1000.0) * high_cpm, 2)

    lifetime_min = round((total_lifetime_views / 1000.0) * low_cpm, 2)
    lifetime_max = round((total_lifetime_views / 1000.0) * high_cpm, 2)

    return {
        "disclaimer": "Estimates only based on CPM formula. Actual earnings depend on audience geo, ad fill rate, and niche.",
        "config": {"low_cpm_usd": low_cpm, "high_cpm_usd": high_cpm},
        "daily": {"min_usd": daily_min, "max_usd": daily_max, "formatted": f"${daily_min:,.2f} - ${daily_max:,.2f}"},
        "monthly": {"min_usd": monthly_min, "max_usd": monthly_max, "formatted": f"${monthly_min:,.2f} - ${monthly_max:,.2f}"},
        "yearly": {"min_usd": yearly_min, "max_usd": yearly_max, "formatted": f"${yearly_min:,.2f} - ${yearly_max:,.2f}"},
        "lifetime": {"min_usd": lifetime_min, "max_usd": lifetime_max, "formatted": f"${lifetime_min:,.2f} - ${lifetime_max:,.2f}"},
    }


def calculate_multiplatform_revenue(platform: str, followers: int, monthly_views: int = 0, avg_engagement_rate: float = 2.0) -> dict:
    """
    Platform specific revenue / sponsorship value calculator.
    """
    platform = (platform or "youtube").lower()
    followers = max(0, followers or 0)
    monthly_views = max(0, monthly_views or 0)
    avg_engagement_rate = max(0.1, avg_engagement_rate or 1.0)

    if platform == "youtube":
        return calculate_estimated_revenue(monthly_views, monthly_views * 10)

    elif platform == "instagram":
        # Estimate sponsorship value per post & reel based on followers and engagement rate
        base_rate = (followers / 1000.0) * 10.0  # Industry benchmark ~$10 per 1k followers
        eng_multiplier = max(0.5, min(3.0, avg_engagement_rate / 2.0))
        sponsored_post_min = round(base_rate * 0.8 * eng_multiplier, 2)
        sponsored_post_max = round(base_rate * 1.5 * eng_multiplier, 2)
        sponsored_reel_min = round(base_rate * 1.2 * eng_multiplier, 2)
        sponsored_reel_max = round(base_rate * 2.2 * eng_multiplier, 2)

        return {
            "platform": "instagram",
            "type": "sponsorship_estimate",
            "disclaimer": "Estimated sponsorship pricing based on follower count & engagement.",
            "sponsored_post": {"min_usd": sponsored_post_min, "max_usd": sponsored_post_max, "formatted": f"${sponsored_post_min:,.2f} - ${sponsored_post_max:,.2f}"},
            "sponsored_reel": {"min_usd": sponsored_reel_min, "max_usd": sponsored_reel_max, "formatted": f"${sponsored_reel_min:,.2f} - ${sponsored_reel_max:,.2f}"},
            "estimated_monthly_brand_deals": {"min_usd": round(sponsored_post_min * 2, 2), "max_usd": round(sponsored_reel_max * 4, 2)},
        }

    elif platform == "facebook":
        # Creator page earnings (in-stream ads + brand partnerships)
        low_cpm = 1.50
        high_cpm = 5.00
        monthly_min = round((monthly_views / 1000.0) * low_cpm, 2)
        monthly_max = round((monthly_views / 1000.0) * high_cpm, 2)
        return {
            "platform": "facebook",
            "type": "creator_earnings_estimate",
            "disclaimer": "Estimated page earnings based on video view volume and average in-stream ad CPM.",
            "monthly": {"min_usd": monthly_min, "max_usd": monthly_max, "formatted": f"${monthly_min:,.2f} - ${monthly_max:,.2f}"},
            "yearly": {"min_usd": round(monthly_min * 12, 2), "max_usd": round(monthly_max * 12, 2)},
        }

    elif platform == "tiktok":
        # Creator Rewards Fund ($0.02 - $0.04 per 1k views) + Sponsorships
        fund_low = round((monthly_views / 1000.0) * 0.02, 2)
        fund_high = round((monthly_views / 1000.0) * 0.04, 2)
        sponsorship_min = round((followers / 1000.0) * 5.0, 2)
        sponsorship_max = round((followers / 1000.0) * 15.0, 2)

        return {
            "platform": "tiktok",
            "type": "creator_fund_and_sponsorship_estimate",
            "disclaimer": "Estimated Creator Rewards Fund + brand integration rates.",
            "creator_fund_monthly": {"min_usd": fund_low, "max_usd": fund_high, "formatted": f"${fund_low:,.2f} - ${fund_high:,.2f}"},
            "sponsored_video": {"min_usd": sponsorship_min, "max_usd": sponsorship_max, "formatted": f"${sponsorship_min:,.2f} - ${sponsorship_max:,.2f}"},
        }

    elif platform == "twitter" or platform == "x":
        # Sponsored tweet pricing based on followers & engagement
        tweet_min = round((followers / 1000.0) * 4.0 * (avg_engagement_rate / 2.0), 2)
        tweet_max = round((followers / 1000.0) * 12.0 * (avg_engagement_rate / 2.0), 2)
        return {
            "platform": "twitter",
            "type": "sponsored_tweet_estimate",
            "disclaimer": "Estimated sponsored post rate based on audience reach and retweets.",
            "sponsored_tweet": {"min_usd": tweet_min, "max_usd": tweet_max, "formatted": f"${tweet_min:,.2f} - ${tweet_max:,.2f}"},
        }

    elif platform == "linkedin":
        # Brand Influence Score (0-100) instead of direct ad CPM
        influence_score = min(100.0, round((followers / 50000.0) * 60.0 + (avg_engagement_rate * 10.0), 1))
        consulting_rate_min = round((followers / 1000.0) * 20.0, 2)
        consulting_rate_max = round((followers / 1000.0) * 50.0, 2)
        return {
            "platform": "linkedin",
            "type": "brand_influence_score",
            "disclaimer": "Brand influence index and B2B thought leadership consulting valuation.",
            "brand_influence_score": influence_score,
            "estimated_b2b_sponsorship": {"min_usd": consulting_rate_min, "max_usd": consulting_rate_max, "formatted": f"${consulting_rate_min:,.2f} - ${consulting_rate_max:,.2f}"},
        }

    return calculate_estimated_revenue(monthly_views)
