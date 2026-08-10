"""Versioned audience analysis job orchestration.

Celery is not part of the current runtime, so this uses a bounded executor as
the local worker.  The job contract is intentionally stage-based and can be
swapped for Celery later without changing the API or dashboard.
"""
from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.video_model import Video
from app.models.video_metric_model import VideoMetric
from app.models.youtube_audience_model import (
    AudienceAnalysisRun,
    AudienceComment,
    AudienceCommentAnalysis,
)
from app.services.audience_ai_service import classify_batch_with_ai, enrich_report
from app.services.audience_intelligence_service import build_report, classify_comment, normalize_text
from app.services.youtube_audience_service import fetch_comments, fetch_video_metadata
from app.utils import utc_now


_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="social-pulse-audience")


def enqueue_analysis(app, run_id: int):
    return _EXECUTOR.submit(_run_analysis, app, run_id)


def _set_stage(run: AudienceAnalysisRun, stage: str, progress: float, **values):
    run.current_stage = stage
    run.progress_pct = max(0.0, min(100.0, float(progress)))
    for key, value in values.items():
        setattr(run, key, value)
    db.session.commit()


def _upsert_video(run: AudienceAnalysisRun, metadata: dict) -> Video:
    video = Video.query.get(run.video_fk_id)
    if not video:
        video = Video(platform="youtube", external_id=run.external_video_id)
        db.session.add(video)
        db.session.flush()
        run.video_fk_id = video.id
    video.title = metadata.get("title")
    video.description = (metadata.get("description") or "")[:10000]
    video.thumbnail_url = metadata.get("thumbnail_url")
    video.published_at = metadata.get("published_at")
    video.tags = []
    db.session.add(VideoMetric(
        video_id=video.id,
        views=metadata.get("views", 0),
        likes=metadata.get("likes", 0),
        comments=metadata.get("comments", 0),
        shares=0,
        engagement_rate=0.0,
    ))
    db.session.commit()
    return video


def _upsert_comments(video: Video, rows: list[dict]) -> list[AudienceComment]:
    # YouTube reply pagination can repeat an ID, and two analyses for the same
    # video can be running at the same time. Collapse the fetched payload first
    # so one run never queues duplicate INSERTs for the unique key.
    unique_rows: dict[str, dict] = {}
    for row in rows:
        external_id = str(row.get("comment_id") or "").strip()
        text = (row.get("text") or "").strip()
        if external_id and text:
            unique_rows[external_id] = row

    existing = {
        row.external_comment_id: row
        for row in AudienceComment.query.filter_by(video_fk_id=video.id).all()
    }
    stored = []

    def apply_row(comment: AudienceComment, row: dict):
        text = (row.get("text") or "").strip()
        comment.parent_external_comment_id = row.get("parent_comment_id")
        comment.author_name = row.get("author_name")
        comment.author_channel_id = row.get("author_channel_id")
        comment.original_text = text
        comment.normalized_text = normalize_text(text)
        comment.like_count = int(row.get("likes", 0) or 0)
        comment.reply_count = int(row.get("replies", 0) or 0)
        comment.published_at = row.get("published_at")
        comment.updated_at = row.get("updated_at")
        comment.last_seen_at = utc_now()

    for external_id, row in unique_rows.items():
        comment = existing.get(external_id)
        if comment is None:
            comment = AudienceComment(video_fk_id=video.id, external_comment_id=external_id)
            db.session.add(comment)
            # Keep new rows in the in-memory map too; this prevents duplicate
            # objects when the same ID appeared more than once in the payload.
            existing[external_id] = comment
        apply_row(comment, row)
        stored.append(comment)

    try:
        db.session.commit()
    except IntegrityError:
        # Another worker may have inserted one of these IDs between our initial
        # SELECT and COMMIT. Re-read after rollback and update the winning row.
        db.session.rollback()
        stored = []
        for external_id, row in unique_rows.items():
            comment = AudienceComment.query.filter_by(
                video_fk_id=video.id,
                external_comment_id=external_id,
            ).first()
            if comment is None:
                comment = AudienceComment(video_fk_id=video.id, external_comment_id=external_id)
                db.session.add(comment)
            apply_row(comment, row)
            stored.append(comment)
        db.session.commit()
    return stored


def _run_analysis(app, run_id: int):
    with app.app_context():
        run = AudienceAnalysisRun.query.get(run_id)
        if not run:
            return
        try:
            run.status = "FETCHING"
            run.started_at = utc_now()
            _set_stage(run, "FETCHING", 8)
            metadata = fetch_video_metadata(run.external_video_id)
            video = _upsert_video(run, metadata)

            count = None if run.requested_all else run.requested_count
            _set_stage(run, "FETCHING", 20)
            fetched = fetch_comments(run.external_video_id, count, run.requested_all)
            rows = fetched.get("comments", [])
            run.available_count = max(int(metadata.get("comments", 0) or 0), len(rows))
            run.fetched_count = len(rows)
            run.configuration_json = {
                **(run.configuration_json or {}),
                "actual_api_pages": int(fetched.get("pages", 0) or 0),
                "actual_quota_units": int(fetched.get("pages", 0) or 0),
            }
            _set_stage(run, "PREPROCESSING", 28, available_count=run.available_count, fetched_count=run.fetched_count)
            stored_comments = _upsert_comments(video, rows)
            run.skipped_count = max(0, len(rows) - len(stored_comments))
            run.unique_count = len({comment.normalized_text for comment in stored_comments if comment.normalized_text})

            previous = (
                AudienceAnalysisRun.query
                .filter(
                    AudienceAnalysisRun.user_id == run.user_id,
                    AudienceAnalysisRun.video_fk_id == video.id,
                    AudienceAnalysisRun.status == "COMPLETED",
                    AudienceAnalysisRun.id != run.id,
                )
                .order_by(AudienceAnalysisRun.created_at.desc())
                .first()
            )
            cached_by_comment_id = {}
            if previous:
                cached_by_comment_id = {
                    analysis.comment.external_comment_id: analysis
                    for analysis in previous.comment_analyses
                    if analysis.comment
                }

            batch_size = int(app.config.get("AUDIENCE_COMMENT_BATCH_SIZE", 150))
            total_batches = max(1, math.ceil(len(stored_comments) / batch_size))
            run.total_batches = total_batches
            run.status = "CLASSIFYING"
            db.session.commit()
            all_analyses: list[dict] = []
            seen_normalized: set[str] = set()
            reused_cached_count = 0
            failed_items: list[dict] = []
            batch_provider_used = "deterministic"
            requested_provider = (run.configuration_json or {}).get("provider", "auto")
            for batch_number in range(total_batches):
                batch = stored_comments[batch_number * batch_size:(batch_number + 1) * batch_size]
                batch_results = []
                raw_batch = [{
                    "comment_id": comment.external_comment_id,
                    "text": comment.original_text,
                    "likes": comment.like_count,
                    "replies": comment.reply_count,
                } for comment in batch]
                reusable_ids = {
                    comment.external_comment_id
                    for comment in batch
                    if (cached_by_comment_id.get(comment.external_comment_id) and (not comment.updated_at or not previous or not previous.completed_at or comment.updated_at <= previous.completed_at))
                }
                ai_batch, provider_used = classify_batch_with_ai([item for item in raw_batch if item["comment_id"] not in reusable_ids], requested_provider)
                if provider_used != "deterministic":
                    batch_provider_used = provider_used
                for comment in batch:
                    raw = {
                        "comment_id": comment.external_comment_id,
                        "text": comment.original_text,
                        "likes": comment.like_count,
                        "replies": comment.reply_count,
                    }
                    cached = cached_by_comment_id.get(comment.external_comment_id)
                    can_reuse = bool(cached and (not comment.updated_at or not previous or not previous.completed_at or comment.updated_at <= previous.completed_at))
                    classification = None
                    for attempt in range(3):
                        try:
                            if can_reuse:
                                classification = {
                                    "language": cached.language,
                                    "sentiment": cached.sentiment,
                                    "emotion": cached.emotion,
                                    "topic": cached.topic,
                                    "intent": cached.intent,
                                    "persona": cached.persona,
                                    "cluster": cached.cluster,
                                    "spam": cached.is_spam,
                                    "toxic": cached.is_toxic,
                                    "toxicity_severity": cached.toxicity_severity,
                                    "sarcastic": cached.is_sarcastic,
                                    "bot_signal": cached.bot_signal,
                                    "quality_score": cached.quality_score,
                                    "confidence": cached.confidence,
                                    "evidence": cached.evidence_json or {},
                                }
                                reused_cached_count += 1
                            elif comment.external_comment_id in ai_batch:
                                classification = ai_batch[comment.external_comment_id]
                            else:
                                classification = classify_comment(raw, seen_normalized)
                            break
                        except Exception as exc:
                            if attempt == 2:
                                failed_items.append({"comment_id": comment.external_comment_id, "error": str(exc)})
                    seen_normalized.add(comment.normalized_text)
                    if classification is None:
                        continue
                    analysis = AudienceCommentAnalysis(
                        run_id=run.id,
                        comment_id=comment.id,
                        language=classification.get("language") or "Unknown",
                        sentiment=classification.get("sentiment") or "Neutral",
                        emotion=classification.get("emotion") or "Uncertain",
                        topic=classification.get("topic") or "Unknown",
                        intent=classification.get("intent") or "Unclear",
                        persona=classification.get("persona") or "Unknown",
                        cluster=classification.get("cluster") or "Unknown",
                        is_spam=bool(classification.get("spam")),
                        is_toxic=bool(classification.get("toxic")),
                        toxicity_severity=classification.get("toxicity_severity"),
                        is_sarcastic=bool(classification.get("sarcastic")),
                        bot_signal=classification.get("bot_signal") or "Likely Organic",
                        quality_score=float(classification.get("quality_score") or 0),
                        confidence=float(classification.get("confidence") or 0),
                        evidence_json=classification.get("evidence") if isinstance(classification.get("evidence"), dict) else {},
                    )
                    db.session.add(analysis)
                    batch_results.append(classification)
                db.session.flush()
                all_analyses.extend(batch_results)
                _set_stage(
                    run,
                    "CLASSIFYING",
                    30 + ((batch_number + 1) / total_batches) * 45,
                    current_batch=batch_number + 1,
                    total_batches=total_batches,
                    analyzed_count=len(all_analyses),
                )
            run.configuration_json = {
                **(run.configuration_json or {}),
                "reused_cached_count": reused_cached_count,
                "batch_provider": batch_provider_used,
            }

            run.status = "CLUSTERING"
            _set_stage(run, "CLUSTERING", 76)
            run.status = "ANALYZING"
            _set_stage(run, "ANALYZING", 78)
            run.status = "AGGREGATING"
            _set_stage(run, "AGGREGATING", 80)
            comments_payload = [comment.to_dict() for comment in stored_comments]
            report = build_report(metadata, comments_payload, all_analyses, previous.report_json if previous else None)
            report["failed_batches"] = failed_items
            run.status = "SUMMARIZING"
            _set_stage(run, "SUMMARIZING", 90)
            report, provider_used = enrich_report(report, comments_payload, requested_provider)
            run.report_json = report
            run.model_used = provider_used if provider_used != "deterministic" else batch_provider_used
            run.failed_count = len(failed_items)
            run.status = "COMPLETED"
            run.current_stage = "COMPLETED"
            run.progress_pct = 100.0
            run.completed_at = utc_now()
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            failed = AudienceAnalysisRun.query.get(run_id)
            if failed:
                failed.status = "FAILED"
                failed.current_stage = "FAILED"
                failed.error_message = str(exc)
                failed.failed_count = max(1, failed.failed_count or 0)
                failed.completed_at = utc_now()
                db.session.commit()
            app.logger.exception("Audience analysis job %s failed", run_id)
        finally:
            db.session.remove()
