"""
Social Pulse API — Multi-Platform Historical Tracker Worker
Runs daily snapshots of YouTube channels, Instagram, Facebook, TikTok, X, and LinkedIn accounts
and posts into ChannelHistory, VideoHistory, AccountHistory, and PostHistory tables.
"""
from datetime import datetime
from app.extensions import db
from app.models.tracked_channel_model import TrackedChannel
from app.models.connected_account_model import ConnectedAccount
from app.models.video_model import Video
from app.models.channel_history_model import ChannelHistory
from app.models.video_history_model import VideoHistory
from app.models.account_history_model import AccountHistory
from app.models.post_history_model import PostHistory
from app.integrations import youtube_client, meta_client, tiktok_client
from app.utils import utc_now


def run_daily_snapshot():
    """
    1. Snapshot YouTube Tracked Channels & Videos.
    2. Snapshot Connected Accounts & Posts (Instagram, Facebook, TikTok, YouTube).
    """
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    snapshots_created = 0

    # 1. Tracked YouTube Channels
    channels = TrackedChannel.query.all()
    for ch in channels:
        info = youtube_client.get_channel_info(ch.channel_id)
        if info:
            ch.subscriber_count = info.get("subscriber_count", ch.subscriber_count or 0)
            ch.total_views = info.get("total_views", ch.total_views or 0)
            if info.get("video_count"):
                ch.total_videos_count = info.get("video_count")
            if info.get("thumbnail"):
                ch.profile_image = info.get("thumbnail")

        # ChannelHistory
        existing_ch = ChannelHistory.query.filter(
            ChannelHistory.channel_id == ch.channel_id,
            db.func.strftime("%Y-%m-%d", ChannelHistory.recorded_at) == today_str
        ).first()

        if not existing_ch:
            db.session.add(ChannelHistory(
                channel_id=ch.channel_id,
                subscribers=ch.subscriber_count or 0,
                total_views=ch.total_views or 0,
                total_videos=ch.video_count or 0,
                recorded_at=utc_now(),
                created_at=utc_now(),
            ))
            snapshots_created += 1

        # VideoHistory
        videos = Video.query.filter_by(tracked_channel_id=ch.id).all()
        for v in videos:
            latest_m = v.get_latest_metric()
            views = latest_m.views if latest_m else 0
            likes = latest_m.likes if latest_m else 0
            comments = latest_m.comments if latest_m else 0
            shares = latest_m.shares if latest_m else 0

            existing_vh = VideoHistory.query.filter(
                VideoHistory.video_id == v.id,
                db.func.strftime("%Y-%m-%d", VideoHistory.recorded_at) == today_str
            ).first()

            if not existing_vh:
                db.session.add(VideoHistory(
                    video_id=v.id,
                    external_id=v.external_id,
                    views=views,
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    recorded_at=utc_now(),
                    created_at=utc_now(),
                ))

    # 2. Connected Accounts across platforms
    accounts = ConnectedAccount.query.all()
    for acc in accounts:
        existing_ah = AccountHistory.query.filter(
            AccountHistory.platform_account_id == acc.platform_account_id,
            AccountHistory.platform == acc.platform,
            db.func.strftime("%Y-%m-%d", AccountHistory.recorded_at) == today_str
        ).first()

        if not existing_ah:
            db.session.add(AccountHistory(
                account_id=acc.id,
                platform=acc.platform,
                platform_account_id=acc.platform_account_id,
                followers=0,
                total_views=0,
                total_posts=len(acc.videos),
                recorded_at=utc_now(),
                created_at=utc_now(),
            ))
            snapshots_created += 1

        # PostHistory for account videos/posts
        for v in acc.videos:
            latest_m = v.get_latest_metric()
            views = latest_m.views if latest_m else 0
            likes = latest_m.likes if latest_m else 0
            comments = latest_m.comments if latest_m else 0
            shares = latest_m.shares if latest_m else 0

            existing_ph = PostHistory.query.filter(
                PostHistory.external_id == v.external_id,
                db.func.strftime("%Y-%m-%d", PostHistory.recorded_at) == today_str
            ).first()

            if not existing_ph:
                db.session.add(PostHistory(
                    post_id=v.id,
                    external_id=v.external_id,
                    platform=v.platform,
                    views=views,
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    recorded_at=utc_now(),
                    created_at=utc_now(),
                ))

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

    return {"status": "success", "snapshots_created": snapshots_created, "channels_processed": len(channels), "accounts_processed": len(accounts)}
