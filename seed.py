"""
Social Pulse API — Seed Script
Run: python seed.py
Seeds the database with demo data for the viva demo.
"""
import sys
import os

# Ensure the app is importable
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.models.user_model import User
from app.models.connected_account_model import ConnectedAccount
from app.models.tracked_channel_model import TrackedChannel
from app.models.video_model import Video
from app.models.video_metric_model import VideoMetric
from app.models.suggestion_model import Suggestion
from app.models.suggestion_source_model import SuggestionSource
from app.utils import utc_now
from datetime import datetime, timedelta

app = create_app()

SEED_VIDEOS = [
    {
        "external_id": "seed_yt_001",
        "title": "How I Built a SaaS in 30 Days with Python",
        "description": "Complete walkthrough of building a profitable SaaS product from scratch.",
        "tags": ["python", "saas", "programming", "startup"],
        "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "duration_seconds": 1842,
        "days_ago": 90,
        "metrics": [
            {"views": 12000, "likes": 890, "comments": 134, "shares": 45, "days_ago": 89},
            {"views": 35000, "likes": 2100, "comments": 310, "shares": 120, "days_ago": 60},
            {"views": 87000, "likes": 5400, "comments": 720, "shares": 380, "days_ago": 30},
        ],
    },
    {
        "external_id": "seed_yt_002",
        "title": "5 Mistakes Every Junior Developer Makes",
        "description": "Avoid these common pitfalls in your early developer career.",
        "tags": ["developer", "career", "programming", "tips"],
        "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "duration_seconds": 923,
        "days_ago": 75,
        "metrics": [
            {"views": 8500, "likes": 620, "comments": 95, "shares": 30, "days_ago": 74},
            {"views": 42000, "likes": 3100, "comments": 420, "shares": 200, "days_ago": 50},
            {"views": 152300, "likes": 8900, "comments": 1200, "shares": 670, "days_ago": 20},
        ],
    },
    {
        "external_id": "seed_yt_003",
        "title": "Next.js 15 Full Course — Build a Real App",
        "description": "Everything you need to know about Next.js 15 App Router.",
        "tags": ["nextjs", "react", "javascript", "webdev"],
        "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "duration_seconds": 7200,
        "days_ago": 60,
        "metrics": [
            {"views": 22000, "likes": 1800, "comments": 280, "shares": 95, "days_ago": 59},
            {"views": 68000, "likes": 4900, "comments": 740, "shares": 320, "days_ago": 35},
            {"views": 195000, "likes": 11200, "comments": 1560, "shares": 870, "days_ago": 10},
        ],
    },
    {
        "external_id": "seed_yt_004",
        "title": "Python Flask REST API — Complete Tutorial 2026",
        "description": "Build a production-ready REST API with Flask, SQLAlchemy, and JWT.",
        "tags": ["flask", "python", "api", "backend"],
        "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "duration_seconds": 5400,
        "days_ago": 45,
        "metrics": [
            {"views": 18000, "likes": 1350, "comments": 215, "shares": 78, "days_ago": 44},
            {"views": 55000, "likes": 4100, "comments": 620, "shares": 290, "days_ago": 25},
            {"views": 128000, "likes": 7800, "comments": 1100, "shares": 580, "days_ago": 8},
        ],
    },
    {
        "external_id": "seed_yt_005",
        "title": "The ONLY Content Strategy You Need in 2026",
        "description": "Stop guessing. Here's the data-driven content strategy that works.",
        "tags": ["contentstrategy", "youtube", "growth", "creator"],
        "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "duration_seconds": 1560,
        "days_ago": 30,
        "metrics": [
            {"views": 31000, "likes": 2400, "comments": 380, "shares": 150, "days_ago": 29},
            {"views": 89000, "likes": 6800, "comments": 950, "shares": 480, "days_ago": 15},
            {"views": 220000, "likes": 14500, "comments": 2100, "shares": 1200, "days_ago": 3},
        ],
    },
    {
        "external_id": "seed_yt_006",
        "title": "Docker & Kubernetes for Beginners — Zero to Production",
        "description": "Containerize your apps and deploy them like a pro.",
        "tags": ["docker", "kubernetes", "devops", "cloud"],
        "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "duration_seconds": 6840,
        "days_ago": 25,
        "metrics": [
            {"views": 14000, "likes": 980, "comments": 145, "shares": 55, "days_ago": 24},
            {"views": 41000, "likes": 3200, "comments": 480, "shares": 230, "days_ago": 12},
        ],
    },
    {
        "external_id": "seed_yt_007",
        "title": "React vs Vue vs Angular in 2026 — Which Should You Learn?",
        "description": "An objective comparison of the big 3 JavaScript frameworks.",
        "tags": ["react", "vue", "angular", "javascript", "frontend"],
        "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "duration_seconds": 1230,
        "days_ago": 20,
        "metrics": [
            {"views": 28000, "likes": 2100, "comments": 320, "shares": 130, "days_ago": 19},
            {"views": 72000, "likes": 5400, "comments": 810, "shares": 410, "days_ago": 7},
        ],
    },
    {
        "external_id": "seed_yt_008",
        "title": "TypeScript Tips & Tricks You Didn't Know",
        "description": "Level up your TypeScript skills with these practical techniques.",
        "tags": ["typescript", "javascript", "programming", "webdev"],
        "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "duration_seconds": 1845,
        "days_ago": 15,
        "metrics": [
            {"views": 19000, "likes": 1450, "comments": 220, "shares": 85, "days_ago": 14},
            {"views": 48000, "likes": 3700, "comments": 560, "shares": 265, "days_ago": 5},
        ],
    },
]

TRACKED_CHANNEL_VIDEOS = [
    {
        "external_id": "tc1_yt_001",
        "title": "Algorithm Mastery: From Beginner to Expert",
        "description": "Competitor channel tutorial on algorithms.",
        "tags": ["algorithms", "competitive", "programming"],
        "duration_seconds": 4800,
        "days_ago": 45,
        "metrics": [{"views": 340000, "likes": 22000, "comments": 3100, "shares": 1800, "days_ago": 44}],
    },
    {
        "external_id": "tc1_yt_002",
        "title": "System Design for Senior Developers",
        "description": "Architecture patterns used at FAANG companies.",
        "tags": ["systemdesign", "architecture", "senior"],
        "duration_seconds": 5400,
        "days_ago": 30,
        "metrics": [{"views": 510000, "likes": 31000, "comments": 4200, "shares": 2700, "days_ago": 29}],
    },
    {
        "external_id": "tc2_yt_001",
        "title": "Build a Viral TikTok Marketing Strategy",
        "description": "How top brands dominate TikTok in 2026.",
        "tags": ["tiktok", "marketing", "viral", "social"],
        "duration_seconds": 1380,
        "days_ago": 20,
        "metrics": [{"views": 780000, "likes": 58000, "comments": 7800, "shares": 12000, "days_ago": 19}],
    },
]


def seed():
    with app.app_context():
        print("🌱 Seeding Social Pulse database...")

        # ── Users ──────────────────────────────────────────────────
        admin_user = User.query.filter_by(email="admin@socialpulse.test").first()
        if not admin_user:
            admin_user = User(
                email="admin@socialpulse.test",
                full_name="Admin User",
                role="admin",
                is_active=True,
                created_at=utc_now(),
            )
            admin_user.set_password("Admin123")
            db.session.add(admin_user)
            print("  ✅ Created admin: admin@socialpulse.test / Admin123")
        else:
            print("  ⏩ Admin user already exists.")

        member_user = User.query.filter_by(email="creator@socialpulse.test").first()
        if not member_user:
            member_user = User(
                email="creator@socialpulse.test",
                full_name="Alex Creator",
                role="member",
                is_active=True,
                created_at=utc_now(),
            )
            member_user.set_password("Member123")
            db.session.add(member_user)
            print("  ✅ Created member: creator@socialpulse.test / Member123")
        else:
            print("  ⏩ Member user already exists.")

        db.session.flush()

        # ── Connected Account ──────────────────────────────────────
        account = ConnectedAccount.query.filter_by(
            user_id=member_user.id, platform="youtube", platform_account_id="UCVHFbw7woebKtX37QMs4Cng"
        ).first()
        if not account:
            account = ConnectedAccount(
                user_id=member_user.id,
                platform="youtube",
                platform_account_id="UCVHFbw7woebKtX37QMs4Cng",
                display_name="Alex Creator — Dev Channel",
                last_synced_at=utc_now() - timedelta(hours=2),
                created_at=utc_now() - timedelta(days=100),
            )
            db.session.add(account)
            db.session.flush()
            print("  ✅ Created connected account: YouTube Dev Channel")
        else:
            print("  ⏩ Connected account already exists.")

        # ── Tracked Channels ───────────────────────────────────────
        tc1 = TrackedChannel.query.filter_by(channel_id="UC-competitor-tech-001").first()
        if not tc1:
            tc1 = TrackedChannel(
                added_by_id=admin_user.id,
                platform="youtube",
                channel_id="UC-competitor-tech-001",
                channel_name="TechGuru Pro",
                niche="Software Engineering",
                created_at=utc_now() - timedelta(days=60),
            )
            db.session.add(tc1)
            print("  ✅ Created tracked channel: TechGuru Pro")
        else:
            print("  ⏩ Tracked channel 1 already exists.")

        tc2 = TrackedChannel.query.filter_by(channel_id="UC-competitor-creator-002").first()
        if not tc2:
            tc2 = TrackedChannel(
                added_by_id=admin_user.id,
                platform="youtube",
                channel_id="UC-competitor-creator-002",
                channel_name="CreatorPulse Academy",
                niche="Content Creation & Marketing",
                created_at=utc_now() - timedelta(days=45),
            )
            db.session.add(tc2)
            print("  ✅ Created tracked channel: CreatorPulse Academy")
        else:
            print("  ⏩ Tracked channel 2 already exists.")

        db.session.flush()

        # ── Seed Videos + Metrics for Connected Account ───────────
        seeded_videos = []
        now = utc_now()
        for v_data in SEED_VIDEOS:
            existing = Video.query.filter_by(platform="youtube", external_id=v_data["external_id"]).first()
            if existing:
                seeded_videos.append(existing)
                continue

            pub_at = now - timedelta(days=v_data["days_ago"])
            video = Video(
                connected_account_id=account.id,
                platform="youtube",
                external_id=v_data["external_id"],
                title=v_data["title"],
                description=v_data["description"],
                tags=v_data["tags"],
                thumbnail_url=v_data["thumbnail_url"],
                duration_seconds=v_data["duration_seconds"],
                published_at=pub_at,
                fetched_at=now,
            )
            db.session.add(video)
            db.session.flush()
            seeded_videos.append(video)

            for m in v_data["metrics"]:
                metric = VideoMetric(
                    video_id=video.id,
                    views=m["views"],
                    likes=m["likes"],
                    comments=m["comments"],
                    shares=m["shares"],
                    engagement_rate=round((m["likes"] + m["comments"] + m["shares"]) / max(m["views"], 1) * 100, 4),
                    recorded_at=now - timedelta(days=m["days_ago"]),
                )
                db.session.add(metric)

        print(f"  ✅ Seeded {len(SEED_VIDEOS)} videos with metrics for connected account")

        # ── Seed Videos for Tracked Channels ──────────────────────
        tc_channels = [tc1, tc2]
        for idx, tv_data in enumerate(TRACKED_CHANNEL_VIDEOS):
            tc = tc_channels[0] if idx < 2 else tc_channels[1]
            existing = Video.query.filter_by(platform="youtube", external_id=tv_data["external_id"]).first()
            if existing:
                continue
            pub_at = now - timedelta(days=tv_data["days_ago"])
            video = Video(
                tracked_channel_id=tc.id,
                platform="youtube",
                external_id=tv_data["external_id"],
                title=tv_data["title"],
                description=tv_data["description"],
                tags=tv_data["tags"],
                duration_seconds=tv_data["duration_seconds"],
                published_at=pub_at,
                fetched_at=now,
            )
            db.session.add(video)
            db.session.flush()
            for m in tv_data["metrics"]:
                metric = VideoMetric(
                    video_id=video.id,
                    views=m["views"], likes=m["likes"], comments=m["comments"], shares=m["shares"],
                    engagement_rate=round((m["likes"] + m["comments"] + m["shares"]) / max(m["views"], 1) * 100, 4),
                    recorded_at=now - timedelta(days=m["days_ago"]),
                )
                db.session.add(metric)
        print("  ✅ Seeded tracked channel videos with metrics")

        # ── Seed Suggestion + SuggestionSources (SIGNATURE) ───────
        existing_suggestion = Suggestion.query.filter_by(user_id=member_user.id, type="title").first()
        if not existing_suggestion:
            suggestion = Suggestion(
                user_id=member_user.id,
                connected_account_id=account.id,
                type="title",
                input_context=f"Account: Alex Creator — Dev Channel | Type: title | Videos analyzed: {len(seeded_videos)}",
                output={
                    "titles": [
                        "How I Grew to 100K Subscribers Using Data (Not Luck)",
                        "The Developer's Guide to Content That Actually Gets Views",
                        "Stop Guessing: Build Your YouTube Strategy Like an Engineer",
                        "I Analyzed 500 Viral Dev Videos — Here's What They Share",
                        "Your Content Is Good. Here's Why Nobody's Watching (Fix This)",
                    ],
                    "reasoning": "Titles use curiosity gaps, social proof, and programmer-specific framing for maximum CTR in the developer niche.",
                },
                created_at=utc_now() - timedelta(hours=12),
            )
            db.session.add(suggestion)
            db.session.flush()

            # Link first 4 videos as sources (SIGNATURE many-to-many)
            for sv in seeded_videos[:4]:
                source = SuggestionSource(
                    suggestion_id=suggestion.id,
                    video_id=sv.id,
                    created_at=utc_now() - timedelta(hours=12),
                )
                db.session.add(source)
            print("  ✅ Created seeded suggestion with 4 source video links (signature many-to-many)")
        else:
            print("  ⏩ Seeded suggestion already exists.")

        # ── Commit everything ──────────────────────────────────────
        db.session.commit()
        print("\n🎉 Seed complete! Social Pulse is ready for the viva demo.")
        print("\nDemo credentials:")
        print("  Admin  → admin@socialpulse.test  / Admin123")
        print("  Member → creator@socialpulse.test / Member123")


if __name__ == "__main__":
    seed()
