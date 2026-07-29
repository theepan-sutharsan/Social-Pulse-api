"""
Social Pulse API — SEO Score Engine
Analyzes video metadata (title length, keyword density, description depth, tags count, thumbnail presence, category)
and produces a 0-100 SEO Score + actionable improvement recommendations.
"""


def analyze_video_seo(video_dict: dict) -> dict:
    title = (video_dict.get("title") or "").strip()
    description = (video_dict.get("description") or "").strip()
    tags = video_dict.get("tags") or []
    thumbnail_url = video_dict.get("thumbnail_url") or ""
    category = video_dict.get("category") or ""

    score = 0
    recommendations = []

    t_len = len(title)
    if 30 <= t_len <= 70:
        score += 30
    elif 15 <= t_len < 30 or 70 < t_len <= 90:
        score += 20
        recommendations.append("Adjust title length to 30-70 characters for optimal search visibility and CTR.")
    elif t_len > 0:
        score += 10
        recommendations.append("Title is too short or too long. Aim for 30-70 impactful characters.")
    else:
        recommendations.append("Video missing title. Add a keyword-rich title.")

    d_len = len(description)
    if d_len >= 250:
        score += 25
    elif d_len >= 100:
        score += 15
        recommendations.append("Expand video description to over 250 characters with detailed timestamps and relevant links.")
    elif d_len > 0:
        score += 8
        recommendations.append("Description is very brief. Add comprehensive summary, timestamps, and keywords.")
    else:
        recommendations.append("Missing video description. Write a detailed 250+ character description.")

    t_count = len(tags)
    if t_count >= 8:
        score += 20
    elif t_count >= 4:
        score += 12
        recommendations.append("Add more targeted tags (aim for 8-15 tags covering broad and niche terms).")
    elif t_count > 0:
        score += 5
        recommendations.append("Very few tags found. Include relevant topic, niche, and brand hashtags/tags.")
    else:
        recommendations.append("No tags found. Add 8-15 relevant search tags.")

    if thumbnail_url:
        score += 15
    else:
        recommendations.append("Missing high-resolution thumbnail image.")

    if category:
        score += 10
    else:
        recommendations.append("Set an explicit video category (e.g. Science & Technology, Education).")

    if not recommendations:
        recommendations.append("Excellent SEO optimization! Keep maintaining strong keyword placement and thumbnail contrast.")

    return {
        "seo_score": score,
        "title_length": t_len,
        "description_length": d_len,
        "tags_count": t_count,
        "has_thumbnail": bool(thumbnail_url),
        "has_category": bool(category),
        "recommendations": recommendations,
    }
