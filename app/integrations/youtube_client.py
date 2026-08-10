"""
Social Pulse API — YouTube Data API v3 Client
API-key based, no OAuth required. Fetches public channel data and videos.
"""
from flask import current_app
from datetime import datetime

import re
from urllib.parse import urlparse

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def _get_api_key() -> str:
    key = current_app.config.get("YOUTUBE_API_KEY", "")
    return key


def parse_youtube_identifier(input_str: str) -> dict:
    """
    Parse a raw user input string (channel ID, handle, or full URL)
    and return a dict with type ('id', 'handle', 'username') and clean value.
    """
    val = (input_str or "").strip()
    if not val:
        return {"type": "id", "value": ""}

    # Parse URL if input starts with http://, https://, or youtube.com
    if val.startswith(("http://", "https://", "www.youtube.com", "youtube.com")):
        if not val.startswith(("http://", "https://")):
            val = "https://" + val
        parsed = urlparse(val)
        path = parsed.path.strip("/")
        
        if path.startswith("@"):
            return {"type": "handle", "value": path}
        elif path.startswith("channel/"):
            parts = path.split("/")
            return {"type": "id", "value": parts[1] if len(parts) > 1 else path}
        elif path.startswith("c/") or path.startswith("user/"):
            parts = path.split("/")
            clean = parts[1] if len(parts) > 1 else path
            return {"type": "handle", "value": f"@{clean}" if not clean.startswith("@") else clean}
        elif path:
            clean = path.split("/")[0]
            if clean.startswith("@"):
                return {"type": "handle", "value": clean}
            elif clean.startswith("UC"):
                return {"type": "id", "value": clean}
            else:
                return {"type": "handle", "value": f"@{clean}"}

    # Handle format starting with @
    if val.startswith("@"):
        return {"type": "handle", "value": val}

    # Channel ID (Starts with UC)
    if val.startswith("UC"):
        return {"type": "id", "value": val}

    # Default fallback
    clean_handle = f"@{val}" if not val.startswith("@") else val
    return {"type": "handle", "value": clean_handle}


def _stub_channel_info(channel_id: str) -> dict:
    """Return mock channel data when no API key is configured."""
    clean_id = channel_id if channel_id.startswith("UC") else f"UC_{channel_id.lstrip('@')[:18]}"
    display_name = f"{channel_id}" if channel_id.startswith("@") else f"Channel ({channel_id[:8]}...)"
    return {
        "channel_id": clean_id,
        "display_name": display_name,
        "description": "Demo data is shown because YOUTUBE_API_KEY is not configured.",
        "subscriber_count": 10000,
        "total_views": 0,
        "video_count": 50,
        "thumbnail": "",
        "data_source": "stub",
    }


def _stub_videos(channel_id: str, max_results: int = 50) -> list:
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
        "System Design Masterclass",
        "Microservices vs Monolith Architecture",
        "PostgreSQL Optimization Guide",
        "Tailwind CSS v4 Deep Dive",
        "Building AI Agents with Python",
    ]
    for i in range(max_results):
        t = base_titles[i % len(base_titles)]
        title = f"{t} (Part {i + 1})" if i >= len(base_titles) else t
        videos.append({
            "external_id": f"yt_stub_{channel_id[:6]}_{i}",
            "title": title,
            "description": f"A detailed video guide on {title.lower()}. Subscribe for more!",
            "tags": ["tutorial", "programming", "tech"],
            "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            "duration_seconds": 300 + (i * 45) % 1800,
            "published_at": f"2026-0{(i % 6) + 1}-{(i % 28) + 1:02d}T10:00:00",
        })
    return videos


def get_channel_info(channel_id: str) -> dict:
    """
    Fetch channel metadata for a YouTube channel ID, Handle (@handle), or URL.
    Falls back to stub data if no API key is set.
    """
    api_key = _get_api_key()
    parsed = parse_youtube_identifier(channel_id)
    target_type = parsed["type"]
    clean_val = parsed["value"]

    if not api_key:
        current_app.logger.warning("YOUTUBE_API_KEY not set — using stub data.")
        return _stub_channel_info(clean_val)

    try:
        import requests
        url = f"{YOUTUBE_API_BASE}/channels"
        
        if target_type == "id":
            params = {"part": "snippet,statistics,brandingSettings", "id": clean_val, "key": api_key}
        elif target_type == "handle":
            params = {"part": "snippet,statistics,brandingSettings", "forHandle": clean_val, "key": api_key}
        else:
            params = {"part": "snippet,statistics,brandingSettings", "forUsername": clean_val.lstrip("@"), "key": api_key}

        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        
        # Fallback query if forHandle failed without @
        if not items and target_type == "handle" and clean_val.startswith("@"):
            params["forHandle"] = clean_val.lstrip("@")
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
        
        # Fallback query using forUsername
        if not items and target_type == "handle":
            params_username = {"part": "snippet,statistics,brandingSettings", "forUsername": clean_val.lstrip("@"), "key": api_key}
            resp = requests.get(url, params=params_username, timeout=10)
            if resp.status_code == 200:
                items = resp.json().get("items", [])

        if not items:
            return {}
            
        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        branding = item.get("brandingSettings", {}).get("image", {})
        return {
            "channel_id": item["id"],
            "display_name": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "total_views": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
            "banner_url": branding.get("bannerExternalUrl", ""),
            "country": snippet.get("country"),
            "data_source": "youtube_api",
        }
    except Exception as e:
        current_app.logger.error(f"YouTube channel fetch error: {e}")
        return _stub_channel_info(clean_val)


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
