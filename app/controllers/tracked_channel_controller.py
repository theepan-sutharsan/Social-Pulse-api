"""
Social Pulse API — Tracked Channel Controller
Admin-only management of YouTube competitor/niche channels.
"""
from flask import jsonify, request
from flask_jwt_extended import get_current_user
from app.extensions import db
from app.models.tracked_channel_model import TrackedChannel
from app.models.video_model import Video
from app.models.video_metric_model import VideoMetric
from app.utils import utc_now
from app.utils.csv_utils import rows_to_csv_response, parse_csv_file
from app.utils.pdf_utils import table_pdf_response
from app.integrations import youtube_client
from datetime import datetime, date

REQUIRED_CSV_COLUMNS = ["channel_id", "channel_name", "niche"]


def _validate_tracked_channel_payload(data: dict, channel_id_to_exclude: str = None) -> list:
    errors = []
    val = (data.get("channel_id") or data.get("handle") or data.get("url") or data.get("channel_input") or "").strip()
    if not val:
        errors.append("channel_id, handle (@name), or channel URL is required.")
    
    # Check uniqueness
    if val:
        parsed = youtube_client.parse_youtube_identifier(val)
        search_id = parsed["value"]
        q = TrackedChannel.query.filter_by(channel_id=search_id)
        existing = q.first()
        if existing and existing.channel_id != channel_id_to_exclude:
            errors.append("This YouTube channel is already being tracked.")
    return errors


def get_tracked_channels():
    channels = TrackedChannel.query.all()
    return jsonify({"tracked_channels": [c.to_dict() for c in channels]}), 200


def create_tracked_channel():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    errors = _validate_tracked_channel_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    raw_input = (
        data.get("channel_id") or data.get("handle") or data.get("url") or data.get("channel_input") or ""
    ).strip()

    # Enrich / resolve from YouTube API
    info = youtube_client.get_channel_info(raw_input)
    canonical_id = info.get("channel_id", raw_input) if info else raw_input
    fallback_name = data.get("channel_name", "").strip() or raw_input
    display_name = info.get("display_name", fallback_name) if info else fallback_name

    # Double check uniqueness for canonical_id
    existing = TrackedChannel.query.filter_by(channel_id=canonical_id).first()
    if existing:
        return jsonify({"error": "This YouTube channel is already being tracked."}), 400

    channel = TrackedChannel(
        added_by_id=user.id,
        platform="youtube",
        channel_id=canonical_id,
        channel_name=display_name,
        niche=data.get("niche", "").strip() or None,
        created_at=utc_now(),
    )
    try:
        db.session.add(channel)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create tracked channel: {str(e)}"}), 500

    return jsonify({"message": "Tracked channel added.", "tracked_channel": channel.to_dict()}), 201


def get_tracked_channel(channel_id: int):
    channel = TrackedChannel.query.get(channel_id)
    if not channel:
        return jsonify({"error": "Tracked channel not found."}), 404
    return jsonify({"tracked_channel": channel.to_dict()}), 200


def delete_tracked_channel(channel_id: int):
    channel = TrackedChannel.query.get(channel_id)
    if not channel:
        return jsonify({"error": "Tracked channel not found."}), 404
    try:
        db.session.delete(channel)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Delete failed: {str(e)}"}), 500
    return jsonify({"message": "Tracked channel removed."}), 200


def sync_tracked_channel(channel_id: int):
    channel = TrackedChannel.query.get(channel_id)
    if not channel:
        return jsonify({"error": "Tracked channel not found."}), 404

    try:
        raw_videos = youtube_client.get_channel_videos(channel.channel_id)
        created = 0
        for rv in raw_videos:
            ext_id = rv.get("external_id", "")
            existing = Video.query.filter_by(platform="youtube", external_id=ext_id).first()
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
                    tracked_channel_id=channel.id,
                    platform="youtube",
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

            # Metric snapshot
            views = rv.get("views", 0) or 0
            likes = rv.get("likes", 0) or 0
            comments = rv.get("comments", 0) or 0
            shares = rv.get("shares", 0) or 0
            engagement = round((likes + comments + shares) / max(views, 1) * 100, 4)
            metric = VideoMetric(
                video_id=video.id,
                views=views, likes=likes, comments=comments, shares=shares,
                engagement_rate=engagement, recorded_at=utc_now(),
            )
            db.session.add(metric)

        db.session.commit()
        return jsonify({
            "message": "Sync complete.",
            "videos_fetched": len(raw_videos),
            "new_videos": created,
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Sync failed: {str(e)}"}), 500


def export_tracked_channels(fmt: str = "csv"):
    channels = TrackedChannel.query.all()
    headers = ["channel_id", "channel_name", "niche"]
    rows = [[c.channel_id, c.channel_name, c.niche or ""] for c in channels]
    filename = f"tracked-channels-{date.today().isoformat()}"

    if fmt == "pdf":
        return table_pdf_response(
            filename + ".pdf",
            "Social Pulse — Tracked Channels",
            headers, rows,
        )
    return rows_to_csv_response(filename + ".csv", headers, rows)


def import_tracked_channels_csv(file_storage):
    user = get_current_user()
    rows, header_errors = parse_csv_file(file_storage, REQUIRED_CSV_COLUMNS)
    if header_errors:
        return jsonify({"errors": header_errors}), 400

    created = skipped = 0
    row_errors = []

    for i, row in enumerate(rows, start=2):
        data = {
            "channel_id": row.get("channel_id", "").strip(),
            "channel_name": row.get("channel_name", "").strip(),
            "niche": row.get("niche", "").strip(),
        }
        errors = _validate_tracked_channel_payload(data)
        if errors:
            row_errors.append({"row": i, "message": "; ".join(errors)})
            continue

        existing = TrackedChannel.query.filter_by(channel_id=data["channel_id"]).first()
        if existing:
            skipped += 1
            continue

        channel = TrackedChannel(
            added_by_id=user.id,
            platform="youtube",
            channel_id=data["channel_id"],
            channel_name=data["channel_name"],
            niche=data["niche"] or None,
            created_at=utc_now(),
        )
        db.session.add(channel)
        created += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Import failed: {str(e)}"}), 500

    return jsonify({"created": created, "skipped": skipped, "errors": row_errors}), 200
