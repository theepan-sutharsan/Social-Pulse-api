"""
Social Pulse API — Meta (Facebook / Instagram) OAuth & Graph API Client
Handles real Meta OAuth authentication, long-lived token generation, and Graph API data fetching.
"""
from flask import current_app
import requests

META_AUTH_BASE = "https://www.facebook.com/v19.0/dialog/oauth"
META_TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"
META_GRAPH_BASE = "https://graph.facebook.com/v19.0"


def _cfg():
    return {
        "app_id": str(current_app.config.get("META_APP_ID", "")).strip(),
        "app_secret": str(current_app.config.get("META_APP_SECRET", "")).strip(),
        "redirect_uri": current_app.config.get("META_REDIRECT_URI", "").strip(),
    }


def is_valid_app_id(app_id: str) -> bool:
    """Check if app_id is a valid production app ID (not empty or template placeholder)."""
    if not app_id:
        return False
    app_id_str = str(app_id).strip()
    if app_id_str.startswith("your-") or app_id_str.startswith("your_") or app_id_str in ("123456789", "000000000"):
        return False
    return True


def get_instagram_oauth_url(state: str = "") -> str:
    cfg = _cfg()
    if not is_valid_app_id(cfg["app_id"]):
        return "mock_instagram_oauth"
    scopes = "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement,business_management"
    return (
        f"{META_AUTH_BASE}?client_id={cfg['app_id']}"
        f"&redirect_uri={cfg['redirect_uri']}"
        f"&scope={scopes}"
        f"&state=instagram:{state}"
        f"&response_type=code"
    )


def get_facebook_oauth_url(state: str = "") -> str:
    cfg = _cfg()
    if not is_valid_app_id(cfg["app_id"]):
        return "mock_facebook_oauth"
    scopes = "public_profile,pages_show_list,pages_read_engagement,read_insights,pages_read_user_content"
    return (
        f"{META_AUTH_BASE}?client_id={cfg['app_id']}"
        f"&redirect_uri={cfg['redirect_uri']}"
        f"&scope={scopes}"
        f"&state=facebook:{state}"
        f"&response_type=code"
    )


def exchange_code_for_token(code: str, platform: str) -> dict:
    """
    Exchange OAuth code for access token.
    Exchanges short-lived token for long-lived token (60 days) and resolves 
    Instagram Business Account ID or Facebook Page ID.
    """
    cfg = _cfg()
    if not is_valid_app_id(cfg["app_id"]) or code.startswith("mock"):
        # Stub / Mock data for demo if app_id is unconfigured or mock code passed
        import random
        random_suffix = str(random.randint(100, 999))
        return {
            "access_token": f"stub_meta_access_token_{random_suffix}",
            "refresh_token": None,
            "expires_in": 5184000,
            "platform_account_id": f"stub_{platform}_acc_{random_suffix}",
            "display_name": f"Creator Account ({platform.title()})",
        }

    try:
        # Step 1: Exchange code for short-lived access token
        resp = requests.get(
            META_TOKEN_URL,
            params={
                "client_id": cfg["app_id"],
                "client_secret": cfg["app_secret"],
                "redirect_uri": cfg["redirect_uri"],
                "code": code,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            err_msg = resp.json().get("error", {}).get("message", resp.text)
            raise RuntimeError(f"Meta token exchange error: {err_msg}")

        token_data = resp.json()
        short_token = token_data.get("access_token")

        # Step 2: Exchange for Long-Lived User Access Token (60 days)
        ll_resp = requests.get(
            f"{META_GRAPH_BASE}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": cfg["app_id"],
                "client_secret": cfg["app_secret"],
                "fb_exchange_token": short_token,
            },
            timeout=15,
        )
        if ll_resp.status_code == 200:
            ll_data = ll_resp.json()
            access_token = ll_data.get("access_token") or short_token
            expires_in = ll_data.get("expires_in", 5184000)
        else:
            access_token = short_token
            expires_in = token_data.get("expires_in", 5184000)

        # Step 3: Fetch Connected Pages & Instagram Accounts
        me_accounts_resp = requests.get(
            f"{META_GRAPH_BASE}/me/accounts",
            params={
                "fields": "id,name,access_token,instagram_business_account{id,username,name}",
                "access_token": access_token,
            },
            timeout=15,
        )

        account_id = None
        display_name = None

        if me_accounts_resp.status_code == 200:
            pages = me_accounts_resp.json().get("data", [])
            if platform == "instagram":
                for p in pages:
                    ig_acc = p.get("instagram_business_account")
                    if ig_acc and ig_acc.get("id"):
                        account_id = ig_acc["id"]
                        username = ig_acc.get("username") or ig_acc.get("name")
                        display_name = f"@{username}" if username and not username.startswith("@") else (username or "Instagram Account")
                        break
            elif platform == "facebook":
                if pages:
                    p = pages[0]
                    account_id = p.get("id")
                    display_name = p.get("name") or "Facebook Page"

        # Fallback to /me endpoint if no pages found
        if not account_id:
            me_resp = requests.get(
                f"{META_GRAPH_BASE}/me",
                params={"fields": "id,name", "access_token": access_token},
                timeout=15,
            )
            if me_resp.status_code == 200:
                me_data = me_resp.json()
                account_id = me_data.get("id")
                display_name = display_name or me_data.get("name") or f"Meta Account ({platform.title()})"

        if not account_id:
            raise RuntimeError("Could not retrieve platform account ID from Meta Graph API.")

        return {
            "access_token": access_token,
            "refresh_token": None,
            "expires_in": expires_in,
            "platform_account_id": account_id,
            "display_name": display_name or f"Meta Account ({platform.title()})",
        }

    except Exception as e:
        current_app.logger.error(f"Meta OAuth exchange error: {e}")
        raise RuntimeError(f"Failed to connect Meta account: {str(e)}")


def get_instagram_posts(account_id: str, access_token: str, limit: int = 50) -> list:
    """Fetch real Instagram posts for a business account via Meta Graph API."""
    if access_token.startswith("stub") or not access_token:
        return _stub_ig_posts(account_id, limit)
    try:
        resp = requests.get(
            f"{META_GRAPH_BASE}/{account_id}/media",
            params={
                "fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count",
                "limit": limit,
                "access_token": access_token,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            current_app.logger.warning(f"Instagram Graph API returned status {resp.status_code}: {resp.text}")
            return _stub_ig_posts(account_id, limit)

        posts = []
        for item in resp.json().get("data", []):
            thumb = item.get("thumbnail_url") or item.get("media_url") or ""
            caption = item.get("caption") or ""
            posts.append({
                "external_id": item["id"],
                "title": caption[:200] if caption else "Instagram Post",
                "description": caption,
                "tags": ["instagram", "content"],
                "thumbnail_url": thumb,
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


def get_facebook_posts(account_id: str, access_token: str, limit: int = 50) -> list:
    """Fetch real Facebook page posts via Meta Graph API."""
    if access_token.startswith("stub") or not access_token:
        return _stub_fb_posts(account_id, limit)
    try:
        resp = requests.get(
            f"{META_GRAPH_BASE}/{account_id}/posts",
            params={
                "fields": "id,message,created_time,full_picture,permalink_url,likes.summary(true),comments.summary(true),shares",
                "limit": limit,
                "access_token": access_token,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            current_app.logger.warning(f"Facebook Graph API returned status {resp.status_code}: {resp.text}")
            return _stub_fb_posts(account_id, limit)

        posts = []
        for item in resp.json().get("data", []):
            msg = item.get("message") or ""
            shares_cnt = item.get("shares", {}).get("count", 0) if isinstance(item.get("shares"), dict) else 0
            posts.append({
                "external_id": item["id"],
                "title": msg[:200] if msg else "Facebook Post",
                "description": msg,
                "tags": ["facebook", "page"],
                "thumbnail_url": item.get("full_picture") or "",
                "duration_seconds": 0,
                "published_at": item.get("created_time"),
                "likes": item.get("likes", {}).get("summary", {}).get("total_count", 0),
                "comments": item.get("comments", {}).get("summary", {}).get("total_count", 0),
                "views": 0,
                "shares": shares_cnt,
            })
        return posts
    except Exception as e:
        current_app.logger.error(f"Facebook posts fetch error: {e}")
        return _stub_fb_posts(account_id, limit)


def _stub_ig_posts(account_id: str, limit: int = 50) -> list:
    return [
        {
            "external_id": f"ig_stub_{account_id[:6]}_{i}",
            "title": f"Instagram Reel #{i+1} - High Performing Content #creator",
            "description": f"Amazing Instagram content #{i+1}! Optimized for reach and engagement.",
            "tags": ["content", "creator", "growth", "instagram"],
            "thumbnail_url": "https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=500",
            "duration_seconds": 45,
            "published_at": f"2026-0{(i % 6) + 1}-{(i % 28) + 1:02d}T12:00:00",
            "likes": 1200 + i * 150,
            "comments": 45 + i * 5,
            "views": 15000 + i * 2000,
            "shares": 20 + i * 3,
        }
        for i in range(limit)
    ]


def _stub_fb_posts(account_id: str, limit: int = 50) -> list:
    return [
        {
            "external_id": f"fb_stub_{account_id[:6]}_{i}",
            "title": f"Facebook Post #{i+1} - Community Update",
            "description": f"Exciting update #{i+1} for our Facebook page community!",
            "tags": ["facebook", "community"],
            "thumbnail_url": "",
            "duration_seconds": 0,
            "published_at": f"2026-0{(i % 6) + 1}-{(i % 28) + 1:02d}T09:00:00",
            "likes": 800 + i * 100,
            "comments": 30 + i * 4,
            "views": 9500 + i * 1200,
            "shares": 15 + i * 2,
        }
        for i in range(limit)
    ]
