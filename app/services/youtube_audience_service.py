"""YouTube Data API helpers for Video Audience Intelligence."""
from __future__ import annotations

import math
import re
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import requests
from flask import current_app


YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,20}$")


class AudienceYouTubeError(Exception):
    """A safe, user-facing YouTube integration error."""


def parse_video_id(raw_url: str) -> str:
    """Extract a YouTube video ID from watch, short, embed, live, or youtu.be URLs."""
    value = (raw_url or "").strip()
    if not value:
        raise AudienceYouTubeError("A YouTube video URL is required.")
    candidate = value if "://" in value else f"https://{value}"
    parsed = urlparse(candidate)
    host = (parsed.netloc or "").lower().split(":", 1)[0]
    path_parts = [part for part in parsed.path.split("/") if part]
    video_id = ""

    if host in {"youtu.be", "www.youtu.be"} and path_parts:
        video_id = path_parts[0]
    elif host.endswith("youtube.com"):
        query_id = parse_qs(parsed.query).get("v", [""])[0]
        if query_id:
            video_id = query_id
        else:
            for marker in ("shorts", "embed", "live", "v"):
                if marker in path_parts:
                    idx = path_parts.index(marker)
                    if idx + 1 < len(path_parts):
                        video_id = path_parts[idx + 1]
                        break

    video_id = video_id.split("?", 1)[0].split("&", 1)[0]
    if not VIDEO_ID_RE.match(video_id):
        raise AudienceYouTubeError("That URL does not contain a valid YouTube video ID.")
    return video_id


def normalize_requested_count(value) -> tuple[int | None, bool]:
    """Return (count, all_available) with strict, bounded validation."""
    if isinstance(value, str) and value.strip().lower() in {"all", "all_available", "all available"}:
        return None, True
    try:
        count = int(value)
    except (TypeError, ValueError):
        raise AudienceYouTubeError("Comment count must be a positive integer or 'all'.")
    max_count = int(current_app.config.get("AUDIENCE_MAX_COMMENTS", 10000))
    if count <= 0 or count > max_count:
        raise AudienceYouTubeError(f"Comment count must be between 1 and {max_count:,}.")
    return count, False


def estimate_usage(count: int | None, all_available: bool = False) -> dict:
    requested = count if count is not None else int(current_app.config.get("AUDIENCE_MAX_COMMENTS", 10000))
    pages = max(1, math.ceil(requested / 100))
    batches = max(1, math.ceil(requested / int(current_app.config.get("AUDIENCE_COMMENT_BATCH_SIZE", 150))))
    return {
        "requested_comments": None if all_available else count,
        "requested_label": "All available" if all_available else f"{count:,}",
        "estimated_api_pages": pages,
        "estimated_ai_batches": batches,
        "estimated_duration_seconds": max(30, batches * 6),
        "estimated_duration_label": "2–5 minutes" if requested >= 1000 else "under 2 minutes",
        "quota_units_estimated": pages,
        "label": "Estimated; actual usage depends on replies and API pagination.",
    }


def _api_key() -> str:
    key = (current_app.config.get("YOUTUBE_API_KEY") or "").strip()
    if not key or key.lower().startswith("your-"):
        raise AudienceYouTubeError("YouTube analysis is unavailable because YOUTUBE_API_KEY is not configured.")
    return key


def _request(endpoint: str, params: dict) -> dict:
    params = {**params, "key": _api_key()}
    try:
        response = requests.get(f"{YOUTUBE_API_BASE}/{endpoint}", params=params, timeout=20)
    except requests.RequestException as exc:
        raise AudienceYouTubeError(f"YouTube could not be reached: {exc}") from exc
    if response.status_code >= 400:
        try:
            reason = response.json().get("error", {}).get("errors", [{}])[0].get("reason")
        except (TypeError, ValueError):
            reason = None
        messages = {
            "commentsDisabled": "Comments are disabled for this video.",
            "quotaExceeded": "The YouTube API quota is exhausted. Try again later.",
            "videoNotFound": "The video was not found or is unavailable.",
        }
        raise AudienceYouTubeError(messages.get(reason, "YouTube rejected the request. Please check the URL and permissions."))
    try:
        return response.json()
    except ValueError as exc:
        raise AudienceYouTubeError("YouTube returned an invalid response.") from exc


def _parse_datetime(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def fetch_video_metadata(video_id: str) -> dict:
    data = _request("videos", {"part": "snippet,statistics,contentDetails", "id": video_id})
    items = data.get("items") or []
    if not items:
        raise AudienceYouTubeError("The video was not found, deleted, or is private.")
    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    content = item.get("contentDetails", {})
    return {
        "external_id": item.get("id", video_id),
        "title": snippet.get("title", "Untitled video"),
        "description": snippet.get("description", ""),
        "thumbnail_url": (snippet.get("thumbnails", {}).get("high", {}) or snippet.get("thumbnails", {}).get("default", {})).get("url", ""),
        "channel_name": snippet.get("channelTitle", ""),
        "channel_id": snippet.get("channelId", ""),
        "published_at": _parse_datetime(snippet.get("publishedAt")),
        "duration": content.get("duration", "PT0S"),
        "views": int(stats.get("viewCount", 0) or 0),
        "likes": int(stats.get("likeCount", 0) or 0),
        "comments": int(stats.get("commentCount", 0) or 0),
    }


def _comment_from_snippet(comment_id: str, snippet: dict, parent_id: str | None = None) -> dict:
    return {
        "comment_id": comment_id,
        "parent_comment_id": parent_id,
        "author_name": snippet.get("authorDisplayName", "Anonymous viewer"),
        "author_channel_id": (snippet.get("authorChannelId") or {}).get("value"),
        "text": snippet.get("textDisplay") or snippet.get("textOriginal") or "",
        "likes": int(snippet.get("likeCount", 0) or 0),
        "replies": 0,
        "published_at": _parse_datetime(snippet.get("publishedAt")),
        "updated_at": _parse_datetime(snippet.get("updatedAt")),
    }


def _fetch_replies(parent_id: str, limit: int) -> list[dict]:
    """Fetch every available reply page for one top-level comment."""
    replies: list[dict] = []
    page_token = None
    seen_ids: set[str] = set()
    while len(replies) < limit:
        params = {
            "part": "snippet",
            "parentId": parent_id,
            "maxResults": 100,
            "textFormat": "plainText",
        }
        if page_token:
            params["pageToken"] = page_token
        data = _request("comments", params)
        for item in data.get("items", []):
            reply_id = item.get("id")
            if reply_id and reply_id not in seen_ids:
                replies.append(_comment_from_snippet(reply_id, item.get("snippet", {}), parent_id))
                seen_ids.add(reply_id)
                if len(replies) >= limit:
                    break
        page_token = data.get("nextPageToken")
        if not page_token or not data.get("items"):
            break
    return replies


def fetch_comments(video_id: str, count: int | None, all_available: bool = False) -> dict:
    """Fetch top-level comments and available replies using commentThreads pagination."""
    target = count if count is not None else int(current_app.config.get("AUDIENCE_MAX_COMMENTS", 10000))
    comments: list[dict] = []
    page_token = None
    pages = 0
    while len(comments) < target:
        params = {
            "part": "snippet,replies",
            "videoId": video_id,
            "maxResults": 100,
            "textFormat": "plainText",
        }
        if page_token:
            params["pageToken"] = page_token
        data = _request("commentThreads", params)
        pages += 1
        for item in data.get("items", []):
            thread = item.get("snippet", {})
            top = thread.get("topLevelComment", {})
            top_id = top.get("id") or item.get("id")
            if top_id:
                parent = _comment_from_snippet(top_id, top.get("snippet", {}))
                parent["replies"] = int(thread.get("totalReplyCount", 0) or 0)
                comments.append(parent)
            inline_replies = []
            seen_reply_ids = set()
            for reply in (item.get("replies", {}) or {}).get("comments", []):
                reply_id = reply.get("id")
                if reply_id and reply_id not in seen_reply_ids:
                    inline_replies.append(_comment_from_snippet(reply_id, reply.get("snippet", {}), top_id))
                    seen_reply_ids.add(reply_id)
            if top_id and int(thread.get("totalReplyCount", 0) or 0) > len(inline_replies) and len(comments) < target:
                inline_replies.extend(_fetch_replies(top_id, target - len(comments)))
            for reply in inline_replies:
                if len(comments) >= target:
                    break
                if reply.get("comment_id") not in {item.get("comment_id") for item in comments}:
                    comments.append(reply)
            if len(comments) >= target:
                break
        page_token = data.get("nextPageToken")
        if not page_token or not data.get("items"):
            break
    return {
        "comments": comments[:target],
        "available_count": max(len(comments), 0),
        "pages": pages,
        "requested_count": count,
        "all_available": all_available,
    }
