"""
Social Pulse API — YouTube Data API v3 Channel Service
Handles channel resolution and last-N video metadata fetching.
"""
import re
import logging
from datetime import datetime, timezone
from flask import current_app
import requests

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeChannelServiceError(Exception):
    """Raised when YouTube Data API calls fail."""
    pass


def _api_key() -> str:
    key = current_app.config.get("YOUTUBE_API_KEY", "")
    if not key:
        raise YouTubeChannelServiceError("YOUTUBE_API_KEY is not configured.")
    return key


def extract_handle_or_id(raw_input: str) -> str:
    """
    Parse various YouTube URL/handle/ID formats into a bare handle or channel ID.
    Examples:
        https://www.youtube.com/@mkbhd  ->  @mkbhd
        https://www.youtube.com/channel/UCBcRF18a7Qf58cCRy5xuWwQ  ->  UCBcRF18a7Qf58cCRy5xuWwQ
        @mkbhd  ->  @mkbhd
        UCBcRF18a7Qf58cCRy5xuWwQ  ->  UCBcRF18a7Qf58cCRy5xuWwQ
    """
    raw = raw_input.strip()
    if "youtube.com" in raw:
        if "/@" in raw:
            handle = raw.split("/@")[1].split("/")[0].split("?")[0]
            return f"@{handle}"
        if "/channel/" in raw:
            return raw.split("/channel/")[1].split("/")[0].split("?")[0]
        if "/c/" in raw:
            return raw.split("/c/")[1].split("/")[0].split("?")[0]
        if "/user/" in raw:
            return raw.split("/user/")[1].split("/")[0].split("?")[0]
    return raw


def resolve_channel(channel_url_or_handle: str) -> dict:
    """
    Accepts a channel URL, @handle, or channel ID.
    Returns channel metadata: channel_id, channel_title, channel_handle, thumbnail_url, subscriber_count.
    """
    handle = extract_handle_or_id(channel_url_or_handle)
    key = _api_key()

    params = {"key": key, "part": "snippet,statistics"}
    if re.match(r"^UC[a-zA-Z0-9_-]{22}$", handle):
        params["id"] = handle
    else:
        params["forHandle"] = handle.lstrip("@")

    try:
        resp = requests.get(f"{YOUTUBE_API_BASE}/channels", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise YouTubeChannelServiceError(f"YouTube API request failed: {e}")

    items = data.get("items", [])
    if not items:
        raise YouTubeChannelServiceError(f"Channel not found for input: {channel_url_or_handle!r}")

    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})

    thumbnails = snippet.get("thumbnails", {})
    thumb_url = (
        thumbnails.get("high", {}).get("url")
        or thumbnails.get("medium", {}).get("url")
        or thumbnails.get("default", {}).get("url")
        or ""
    )

    return {
        "channel_id": item["id"],
        "channel_title": snippet.get("title", ""),
        "channel_handle": snippet.get("customUrl", handle),
        "thumbnail_url": thumb_url,
        "subscriber_count": int(stats.get("subscriberCount", 0)),
    }


def fetch_last_n_videos(channel_id: str, n: int = 50) -> list[dict]:
    """
    Fetch last N videos for a channel using uploads playlist (efficient, minimal quota usage).
    Returns a list of video metadata dicts.
    """
    key = _api_key()

    # Step 1: Get uploads playlist ID
    try:
        params = {"key": key, "part": "contentDetails", "id": channel_id}
        resp = requests.get(f"{YOUTUBE_API_BASE}/channels", params=params, timeout=15)
        resp.raise_for_status()
        ch_data = resp.json()
    except requests.RequestException as e:
        raise YouTubeChannelServiceError(f"Failed to fetch channel content details: {e}")

    items = ch_data.get("items", [])
    if not items:
        raise YouTubeChannelServiceError(f"Channel {channel_id} not found when fetching uploads playlist.")

    uploads_playlist_id = (
        items[0]
        .get("contentDetails", {})
        .get("relatedPlaylists", {})
        .get("uploads", "")
    )
    if not uploads_playlist_id:
        raise YouTubeChannelServiceError("Could not resolve uploads playlist for channel.")

    # Step 2: Paginate playlistItems to collect video IDs
    video_ids: list[str] = []
    page_token = None

    while len(video_ids) < n:
        params = {
            "key": key,
            "part": "contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": min(50, n - len(video_ids)),
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            resp = requests.get(f"{YOUTUBE_API_BASE}/playlistItems", params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            raise YouTubeChannelServiceError(f"Failed to fetch playlist items: {e}")

        for item in data.get("items", []):
            vid_id = item.get("contentDetails", {}).get("videoId")
            if vid_id:
                video_ids.append(vid_id)

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    if not video_ids:
        raise YouTubeChannelServiceError("No videos found for this channel.")

    # Step 3: Batch fetch video details + statistics (max 50 IDs per call)
    videos: list[dict] = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        params = {
            "key": key,
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(batch),
        }
        try:
            resp = requests.get(f"{YOUTUBE_API_BASE}/videos", params=params, timeout=15)
            resp.raise_for_status()
            for item in resp.json().get("items", []):
                videos.append(_parse_video_item(item))
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch video batch starting at {i}: {e}")
            continue

    return videos


def _parse_video_item(item: dict) -> dict:
    """Parse a YouTube API video item into a flat dict."""
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    content = item.get("contentDetails", {})

    thumbnails = snippet.get("thumbnails", {})
    thumb = (
        thumbnails.get("high", {}).get("url")
        or thumbnails.get("medium", {}).get("url")
        or thumbnails.get("default", {}).get("url")
        or ""
    )

    published_raw = snippet.get("publishedAt")
    published_at = None
    if published_raw:
        try:
            published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
        except Exception:
            published_at = None

    return {
        "video_id": item["id"],
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "tags": snippet.get("tags", []),
        "published_at": published_at,
        "duration_seconds": _parse_iso8601_duration(content.get("duration", "PT0S")),
        "view_count": int(stats.get("viewCount", 0)),
        "like_count": int(stats.get("likeCount", 0)),
        "comment_count": int(stats.get("commentCount", 0)),
        "thumbnail_url": thumb,
    }


def _parse_iso8601_duration(duration: str) -> int:
    """Convert ISO 8601 duration (PT#H#M#S) to total seconds."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration or "PT0S")
    if not match:
        return 0
    h, m, s = (int(x) if x else 0 for x in match.groups())
    return h * 3600 + m * 60 + s
