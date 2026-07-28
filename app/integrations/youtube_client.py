"""
Social Pulse API — YouTube Data API v3 Client
API-key based, no OAuth required. Fetches public channel data and videos.
"""
from flask import current_app
from datetime import datetime

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def _get_api_key() -> str:
    key = current_app.config.get("YOUTUBE_API_KEY", "")
    return key


def _stub_channel_info(channel_id: str) -> dict:
    """Return mock channel data when no API key is configured."""
    return {
        "channel_id": channel_id,
        "display_name": f"Channel ({channel_id[:8]}...)",
        "subscriber_count": 10000,
        "video_count": 50,
        "thumbnail": "",
    }


def _stub_videos(channel_id: str, max_results: int = 20) -> list:
    """Return mock video data when no API key is configured."""
    videos = []
    base_titles = [
        "How I Built a SaaS in 30 Days",
        "5 Mistakes Every Developer Makes",
        "Next.js 15 Full Course 2026",
        "Python Flask REST API Tutorial",
        "React vs Vue vs Angular in 2026",
        "The BEST AI Tools for Developers",
        "Build a Full Stack App in 1 Hour",
        "Docker & Kubernetes for Beginners",
        "Git Workflow for Teams",
        "TypeScript Tips You Didn't Know",
    ]
    for i, t in enumerate(base_titles[:max_results]):
        videos.append({
            "external_id": f"yt_stub_{channel_id[:6]}_{i}",
            "title": t,
            "description": f"A great video about {t.lower()}. Subscribe for more content!",
            "tags": ["tutorial", "programming", "developer"],
            "thumbnail_url": f"https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            "duration_seconds": 600 + i * 120,
            "published_at": f"2026-0{(i % 6) + 1}-{(i % 28) + 1:02d}T10:00:00",
        })
    return videos


def get_channel_info(channel_id: str) -> dict:
    """
    Fetch channel metadata for the given YouTube channel ID.
    Falls back to stub data if no API key is set.
    """
    api_key = _get_api_key()
    if not api_key:
        current_app.logger.warning("YOUTUBE_API_KEY not set — using stub data.")
        return _stub_channel_info(channel_id)

    try:
        import requests
        url = f"{YOUTUBE_API_BASE}/channels"
        params = {
            "part": "snippet,statistics",
            "id": channel_id,
            "key": api_key,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            return {}
        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        return {
            "channel_id": item["id"],
            "display_name": snippet.get("title", ""),
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
        }
    except Exception as e:
        current_app.logger.error(f"YouTube channel fetch error: {e}")
        return _stub_channel_info(channel_id)


def get_channel_videos(channel_id: str, max_results: int = 20) -> list:
    """
    Fetch the latest videos for a YouTube channel.
    Falls back to stub data if no API key is set.
    """
    api_key = _get_api_key()
    if not api_key:
        current_app.logger.warning("YOUTUBE_API_KEY not set — using stub data.")
        return _stub_videos(channel_id, max_results)

    try:
        import requests
        # Step 1: Search for channel uploads
        search_url = f"{YOUTUBE_API_BASE}/search"
        search_params = {
            "part": "id",
            "channelId": channel_id,
            "maxResults": max_results,
            "order": "date",
            "type": "video",
            "key": api_key,
        }
        search_resp = requests.get(search_url, params=search_params, timeout=10)
        search_resp.raise_for_status()
        video_ids = [
            item["id"]["videoId"]
            for item in search_resp.json().get("items", [])
            if item.get("id", {}).get("videoId")
        ]
        if not video_ids:
            return []

        # Step 2: Get video details
        videos_url = f"{YOUTUBE_API_BASE}/videos"
        video_params = {
            "part": "snippet,contentDetails,statistics",
            "id": ",".join(video_ids),
            "key": api_key,
        }
        videos_resp = requests.get(videos_url, params=video_params, timeout=10)
        videos_resp.raise_for_status()
        results = []
        for item in videos_resp.json().get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            duration_str = item.get("contentDetails", {}).get("duration", "PT0S")
            duration_secs = _parse_iso8601_duration(duration_str)
            pub_at = snippet.get("publishedAt", "")
            try:
                pub_dt = datetime.fromisoformat(pub_at.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pub_dt = None
            results.append({
                "external_id": item["id"],
                "title": snippet.get("title", ""),
                "description": snippet.get("description", "")[:2000],
                "tags": snippet.get("tags", []),
                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                "duration_seconds": duration_secs,
                "published_at": pub_dt,
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
            })
        return results
    except Exception as e:
        current_app.logger.error(f"YouTube videos fetch error: {e}")
        return _stub_videos(channel_id, max_results)


def _parse_iso8601_duration(duration: str) -> int:
    """Parse ISO 8601 duration string (e.g. PT4M13S) into total seconds."""
    import re
    pattern = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
    match = pattern.match(duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds
