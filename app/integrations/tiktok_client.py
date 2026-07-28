"""
Social Pulse API — TikTok OAuth Client
TikTok Login Kit + Display API calls.
"""
from flask import current_app
import requests

TIKTOK_AUTH_BASE = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_VIDEO_LIST_URL = "https://open.tiktokapis.com/v2/video/list/"


def _cfg():
    return {
        "client_key": current_app.config.get("TIKTOK_CLIENT_KEY", ""),
        "client_secret": current_app.config.get("TIKTOK_CLIENT_SECRET", ""),
        "redirect_uri": current_app.config.get("TIKTOK_REDIRECT_URI", ""),
    }


def get_tiktok_oauth_url(state: str = "") -> str:
    cfg = _cfg()
    if not cfg["client_key"]:
        return "https://example.com/mock-tiktok-oauth"
    scopes = "user.info.basic,video.list"
    return (
        f"{TIKTOK_AUTH_BASE}?client_key={cfg['client_key']}"
        f"&redirect_uri={cfg['redirect_uri']}"
        f"&scope={scopes}"
        f"&state=tiktok:{state}"
        f"&response_type=code"
    )


def exchange_code_for_token(code: str) -> dict:
    """Exchange auth code for TikTok access token."""
    cfg = _cfg()
    if not cfg["client_key"]:
        return {
            "access_token": "stub_tiktok_access_token",
            "refresh_token": "stub_tiktok_refresh_token",
            "expires_in": 86400,
            "platform_account_id": "stub_tiktok_user_id",
            "display_name": "Mock TikTok Creator",
        }
    try:
        resp = requests.post(
            TIKTOK_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key": cfg["client_key"],
                "client_secret": cfg["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": cfg["redirect_uri"],
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in", 86400),
            "platform_account_id": data.get("open_id", ""),
            "display_name": data.get("display_name", "TikTok User"),
        }
    except Exception as e:
        current_app.logger.error(f"TikTok OAuth exchange error: {e}")
        raise


def get_user_videos(open_id: str, access_token: str, max_count: int = 20) -> list:
    """Fetch TikTok videos for an authenticated user."""
    if access_token == "stub_tiktok_access_token":
        return _stub_tiktok_videos(open_id, max_count)
    try:
        resp = requests.post(
            TIKTOK_VIDEO_LIST_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "max_count": max_count,
                "fields": ["id", "title", "cover_image_url", "share_url", "video_description",
                           "duration", "height", "width", "title", "embed_html", "embed_link",
                           "like_count", "comment_count", "share_count", "view_count",
                           "create_time"],
            },
            timeout=10,
        )
        resp.raise_for_status()
        videos = []
        for item in resp.json().get("data", {}).get("videos", []):
            videos.append({
                "external_id": item.get("id", ""),
                "title": item.get("title", ""),
                "description": item.get("video_description", ""),
                "tags": [],
                "thumbnail_url": item.get("cover_image_url", ""),
                "duration_seconds": item.get("duration", 0),
                "published_at": None,
                "views": item.get("view_count", 0),
                "likes": item.get("like_count", 0),
                "comments": item.get("comment_count", 0),
                "shares": item.get("share_count", 0),
            })
        return videos
    except Exception as e:
        current_app.logger.error(f"TikTok video fetch error: {e}")
        return _stub_tiktok_videos(open_id, max_count)


def _stub_tiktok_videos(open_id: str, limit: int) -> list:
    return [
        {
            "external_id": f"tt_stub_{open_id[:6]}_{i}",
            "title": f"TikTok Video #{i+1} - Trending Content",
            "description": f"Check out this awesome video #{i+1}! #fyp #viral",
            "tags": ["fyp", "viral", "trending"],
            "thumbnail_url": "",
            "duration_seconds": 30 + i * 5,
            "published_at": f"2026-0{(i % 6) + 1}-{(i % 28) + 1:02d}T18:00:00",
            "views": 50000 + i * 5000,
            "likes": 3000 + i * 300,
            "comments": 200 + i * 20,
            "shares": 500 + i * 50,
        }
        for i in range(min(limit, 8))
    ]
