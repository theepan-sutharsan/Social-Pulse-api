"""
Social Pulse API — Account Controller
Manages connected platform accounts (YouTube public + OAuth).
"""
from datetime import datetime
from flask import jsonify, request
from flask_jwt_extended import get_current_user
from app.extensions import db
from app.models.connected_account_model import ConnectedAccount
from app.models.video_model import Video
from app.models.video_metric_model import VideoMetric
from app.utils import utc_now
from app.utils.csv_utils import rows_to_csv_response
from app.integrations import youtube_client, meta_client, tiktok_client


def _validate_youtube_payload(data: dict) -> list:
    errors = []
    if not data.get("channel_id", "").strip():
        errors.append("channel_id is required.")
    return errors


def get_accounts():
    user = get_current_user()
    if user.role == "admin":
        accounts = ConnectedAccount.query.all()
    else:
        accounts = ConnectedAccount.query.filter_by(user_id=user.id).all()
    return jsonify({"accounts": [a.to_dict() for a in accounts]}), 200


def connect_youtube():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    errors = _validate_youtube_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    channel_id = data["channel_id"].strip()

    # Check for duplicate
    existing = ConnectedAccount.query.filter_by(
        user_id=user.id, platform="youtube", platform_account_id=channel_id
    ).first()
    if existing:
        return jsonify({"error": "This YouTube channel is already connected."}), 400

    # Fetch channel info
    info = youtube_client.get_channel_info(channel_id)
    if not info:
        return jsonify({"error": "YouTube channel not found. Please check the channel ID."}), 404

    account = ConnectedAccount(
        user_id=user.id,
        platform="youtube",
        platform_account_id=channel_id,
        display_name=info.get("display_name", channel_id),
        created_at=utc_now(),
    )
    try:
        db.session.add(account)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to connect account: {str(e)}"}), 500

    return jsonify({"message": "YouTube channel connected.", "account": account.to_dict()}), 201


def get_instagram_oauth_url():
    user = get_current_user()
    url = meta_client.get_instagram_oauth_url(state=str(user.id))
    is_mock = "mock" in url or not meta_client.is_valid_app_id(meta_client._cfg()["app_id"])
    return jsonify({"oauth_url": url, "is_mock": is_mock}), 200


def get_facebook_oauth_url():
    user = get_current_user()
    url = meta_client.get_facebook_oauth_url(state=str(user.id))
    is_mock = "mock" in url or not meta_client.is_valid_app_id(meta_client._cfg()["app_id"])
    return jsonify({"oauth_url": url, "is_mock": is_mock}), 200


def get_tiktok_oauth_url():
    user = get_current_user()
    url = tiktok_client.get_tiktok_oauth_url(state=str(user.id))
    is_mock = "mock" in url or not tiktok_client.is_valid_client_key(tiktok_client._cfg()["client_key"])
    return jsonify({"oauth_url": url, "is_mock": is_mock}), 200


def oauth_callback():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    code = data.get("code", "").strip()
    platform = data.get("platform", "").strip()

    if not code or platform not in ("instagram", "facebook", "tiktok"):
        return jsonify({"errors": ["code and valid platform are required."]}), 400

    try:
        if platform in ("instagram", "facebook"):
            token_data = meta_client.exchange_code_for_token(code, platform)
        else:
            token_data = tiktok_client.exchange_code_for_token(code)
    except Exception as e:
        return jsonify({"error": f"OAuth exchange failed: {str(e)}"}), 400

    existing = ConnectedAccount.query.filter_by(
        user_id=user.id,
        platform=platform,
        platform_account_id=token_data["platform_account_id"],
    ).first()
    if existing:
        return jsonify({"error": "This account is already connected."}), 400

    expires_at = None
    if token_data.get("expires_in"):
        from datetime import timedelta
        expires_at = utc_now() + timedelta(seconds=token_data["expires_in"])

    account = ConnectedAccount(
        user_id=user.id,
        platform=platform,
        platform_account_id=token_data["platform_account_id"],
        display_name=token_data["display_name"],
        access_token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_expires_at=expires_at,
        created_at=utc_now(),
    )
    try:
        db.session.add(account)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to save account: {str(e)}"}), 500

    return jsonify({"message": f"{platform.title()} account connected.", "account": account.to_dict()}), 201


def delete_account(account_id: int):
    user = get_current_user()
    account = ConnectedAccount.query.get(account_id)
    if not account:
        return jsonify({"error": "Account not found."}), 404
    if user.role != "admin" and account.user_id != user.id:
        return jsonify({"error": "Forbidden."}), 403

    try:
        db.session.delete(account)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Delete failed: {str(e)}"}), 500

    return jsonify({"message": "Account disconnected successfully."}), 200


def sync_account(account_id: int):
    user = get_current_user()
    account = ConnectedAccount.query.get(account_id)
    if not account:
        return jsonify({"error": "Account not found."}), 404
    if user.role != "admin" and account.user_id != user.id:
        return jsonify({"error": "Forbidden."}), 403

    try:
        if account.platform == "youtube":
            raw_videos = youtube_client.get_channel_videos(account.platform_account_id)
        elif account.platform == "instagram":
            raw_videos = meta_client.get_instagram_posts(
                account.platform_account_id, account.access_token or ""
            )
        elif account.platform == "facebook":
            raw_videos = meta_client.get_facebook_posts(
                account.platform_account_id, account.access_token or ""
            )
        elif account.platform == "tiktok":
            raw_videos = tiktok_client.get_user_videos(
                account.platform_account_id, account.access_token or ""
            )
        else:
            raw_videos = []

        created = 0
        for rv in raw_videos:
            ext_id = rv.get("external_id", "")
            existing = Video.query.filter_by(
                platform=account.platform, external_id=ext_id
            ).first()
            if existing:
                video = existing
            else:
                pub_at = rv.get("published_at")
                if isinstance(pub_at, str):
                    try:
                        pub_at = datetime.fromisoformat(pub_at.replace("Z", "+00:00")).replace(tzinfo=None)
                    except Exception:
                        pub_at = None

                video = Video(
                    connected_account_id=account.id,
                    platform=account.platform,
                    external_id=ext_id,
                    title=rv.get("title", ""),
                    description=rv.get("description", ""),
                    tags=rv.get("tags", []),
                    thumbnail_url=rv.get("thumbnail_url", ""),
                    duration_seconds=rv.get("duration_seconds"),
                    published_at=pub_at,
                    fetched_at=utc_now(),
                )
                db.session.add(video)
                db.session.flush()
                created += 1

            # Add metric snapshot
            views = rv.get("views", 0) or 0
            likes = rv.get("likes", 0) or 0
            comments = rv.get("comments", 0) or 0
            shares = rv.get("shares", 0) or 0
            engagement = round(
                (likes + comments + shares) / max(views, 1) * 100, 4
            )
            metric = VideoMetric(
                video_id=video.id,
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                engagement_rate=engagement,
                recorded_at=utc_now(),
            )
            db.session.add(metric)

        account.last_synced_at = utc_now()
        db.session.commit()
        return jsonify({
            "message": "Sync complete.",
            "videos_fetched": len(raw_videos),
            "new_videos": created,
            "account": account.to_dict(),
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Sync failed: {str(e)}"}), 500


def export_accounts_csv():
    accounts = ConnectedAccount.query.all()
    headers = ["id", "user_id", "platform", "platform_account_id", "display_name", "last_synced_at", "created_at"]
    rows = [
        [
            a.id, a.user_id, a.platform, a.platform_account_id, a.display_name,
            a.last_synced_at.isoformat() if a.last_synced_at else "",
            a.created_at.isoformat() if a.created_at else "",
        ]
        for a in accounts
    ]
    from datetime import date
    filename = f"accounts-{date.today().isoformat()}.csv"
    return rows_to_csv_response(filename, headers, rows)
