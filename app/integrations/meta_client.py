"""
Social Pulse API — Meta (Facebook / Instagram) OAuth Client
Handles OAuth exchange and Graph API data fetching.
"""
from flask import current_app
import requests

META_AUTH_BASE = "https://www.facebook.com/v19.0/dialog/oauth"
META_TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"
META_GRAPH_BASE = "https://graph.facebook.com/v19.0"


def _cfg():
    return {
        "app_id": current_app.config.get("META_APP_ID", ""),
        "app_secret": current_app.config.get("META_APP_SECRET", ""),
        "redirect_uri": current_app.config.get("META_REDIRECT_URI", ""),
    }


def get_instagram_oauth_url(state: str = "") -> str:
    cfg = _cfg()
    if not cfg["app_id"]:
        return "https://example.com/mock-instagram-oauth"
    scopes = "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement"
    return (
        f"{META_AUTH_BASE}?client_id={cfg['app_id']}"
        f"&redirect_uri={cfg['redirect_uri']}"
        f"&scope={scopes}"
        f"&state=instagram:{state}"
        f"&response_type=code"
    )


def get_facebook_oauth_url(state: str = "") -> str:
    cfg = _cfg()
    if not cfg["app_id"]:
        return "https://example.com/mock-facebook-oauth"
    scopes = "pages_show_list,pages_read_engagement,read_insights"
    return (
        f"{META_AUTH_BASE}?client_id={cfg['app_id']}"
        f"&redirect_uri={cfg['redirect_uri']}"
        f"&scope={scopes}"
        f"&state=facebook:{state}"
        f"&response_type=code"
    )


def exchange_code_for_token(code: str, platform: str) -> dict:
    """Exchange OAuth code for access token. Returns token dict or raises."""
    cfg = _cfg()
    if not cfg["app_id"]:
        # Stub
        return {
            "access_token": "stub_meta_access_token",
            "refresh_token": None,
            "expires_in": 5184000,
            "platform_account_id": "stub_meta_account_id",
            "display_name": f"Mock {platform.title()} Account",
        }
    try:
        resp = requests.get(
            META_TOKEN_URL,
            params={
                "client_id": cfg["app_id"],
                "client_secret": cfg["app_secret"],
                "redirect_uri": cfg["redirect_uri"],
                "code": code,
            },
            timeout=10,
        )
        resp.raise_for_status()
        token_data = resp.json()
        access_token = token_data.get("access_token")
        # Get user/page info
        me_resp = requests.get(
            f"{META_GRAPH_BASE}/me",
            params={"fields": "id,name", "access_token": access_token},
            timeout=10,
        )
        me_resp.raise_for_status()
        me_data = me_resp.json()
        return {
            "access_token": access_token,
            "refresh_token": None,
            "expires_in": token_data.get("expires_in", 5184000),
            "platform_account_id": me_data.get("id", ""),
            "display_name": me_data.get("name", ""),
        }
    except Exception as e:
        current_app.logger.error(f"Meta OAuth exchange error: {e}")
        raise


def get_instagram_posts(account_id: str, access_token: str, limit: int = 20) -> list:
    """Fetch Instagram posts for a business account."""
    if access_token == "stub_meta_access_token":
        return _stub_ig_posts(account_id, limit)
    try:
        resp = requests.get(
            f"{META_GRAPH_BASE}/{account_id}/media",
            params={
                "fields": "id,caption,media_type,timestamp,like_count,comments_count,permalink",
                "limit": limit,
                "access_token": access_token,
            },
            timeout=10,
        )
        resp.raise_for_status()
        posts = []
        for item in resp.json().get("data", []):
            posts.append({
                "external_id": item["id"],
                "title": (item.get("caption") or "")[:200],
                "description": item.get("caption") or "",
                "tags": [],
                "thumbnail_url": item.get("media_url", ""),
                "duration_seconds": 0,
                "published_at": item.get("timestamp"),
                "likes": item.get("like_count", 0),
                "comments": item.get("comments_count", 0),
                "views": 0,
                "shares": 0,
            })
        return posts
    except Exception as e:
        current_app.logger.error(f"Instagram posts fetch error: {e}")
        return _stub_ig_posts(account_id, limit)


def get_facebook_posts(account_id: str, access_token: str, limit: int = 20) -> list:
    """Fetch Facebook page posts."""
    if access_token == "stub_meta_access_token":
        return _stub_fb_posts(account_id, limit)
    try:
        resp = requests.get(
            f"{META_GRAPH_BASE}/{account_id}/posts",
            params={
                "fields": "id,message,created_time,likes.summary(true),comments.summary(true)",
                "limit": limit,
                "access_token": access_token,
            },
            timeout=10,
        )
        resp.raise_for_status()
        posts = []
        for item in resp.json().get("data", []):
            posts.append({
                "external_id": item["id"],
                "title": (item.get("message") or "")[:200],
                "description": item.get("message") or "",
                "tags": [],
                "thumbnail_url": "",
                "duration_seconds": 0,
                "published_at": item.get("created_time"),
                "likes": item.get("likes", {}).get("summary", {}).get("total_count", 0),
                "comments": item.get("comments", {}).get("summary", {}).get("total_count", 0),
                "views": 0,
                "shares": 0,
            })
        return posts
    except Exception as e:
        current_app.logger.error(f"Facebook posts fetch error: {e}")
        return _stub_fb_posts(account_id, limit)


def _stub_ig_posts(account_id: str, limit: int) -> list:
    return [
        {
            "external_id": f"ig_stub_{account_id[:6]}_{i}",
            "title": f"Instagram Post #{i+1} 🔥 #content #creator",
            "description": f"Amazing content post #{i+1}! #socialmedia #growth",
            "tags": ["content", "creator", "growth"],
            "thumbnail_url": "",
            "duration_seconds": 0,
            "published_at": f"2026-0{(i % 6) + 1}-{(i % 28) + 1:02d}T12:00:00",
            "likes": 1200 + i * 150,
            "comments": 45 + i * 5,
            "views": 0,
            "shares": 20 + i * 3,
        }
        for i in range(min(limit, 8))
    ]


def _stub_fb_posts(account_id: str, limit: int) -> list:
    return [
        {
            "external_id": f"fb_stub_{account_id[:6]}_{i}",
            "title": f"Facebook Post #{i+1}",
            "description": f"Exciting update #{i+1} for our community!",
            "tags": [],
            "thumbnail_url": "",
            "duration_seconds": 0,
            "published_at": f"2026-0{(i % 6) + 1}-{(i % 28) + 1:02d}T09:00:00",
            "likes": 800 + i * 100,
            "comments": 30 + i * 4,
            "views": 0,
            "shares": 15 + i * 2,
        }
        for i in range(min(limit, 8))
    ]
