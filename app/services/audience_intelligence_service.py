"""Evidence-based comment classification and audience intelligence aggregation."""
from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from statistics import mean


POSITIVE_WORDS = {
    "amazing", "awesome", "clear", "excellent", "helpful", "love", "loved", "best", "thanks", "thank", "great", "useful", "perfect", "brilliant", "easy", "good", "insightful", "valuable", "excited", "works"
}
NEGATIVE_WORDS = {
    "bad", "boring", "confusing", "confused", "difficult", "hard", "hate", "hated", "issue", "problem", "slow", "unclear", "wrong", "waste", "disappointed", "disappointing", "terrible", "poor", "noise", "missing", "fast"
}
TOXIC_WORDS = {"idiot", "stupid", "dumb", "moron", "hate you", "shut up", "scam", "trash"}
SPAM_WORDS = {"subscribe to my", "check my channel", "free crypto", "whatsapp", "telegram", "dm me", "promo", "affiliate"}
TOPIC_RULES = (
    ("Audio", {"audio", "sound", "volume", "mic", "microphone", "noise"}),
    ("Explanation", {"explain", "understand", "confus", "clarif", "meaning"}),
    ("Tutorial / How-to", {"tutorial", "step", "code", "install", "setup", "example", "how do"}),
    ("Part 2 / Follow-up", {"part 2", "part two", "next video", "more on", "follow up", "series"}),
    ("Resources", {"source", "github", "link", "download", "slides", "resource"}),
    ("Pricing / Product", {"price", "pricing", "cost", "buy", "purchase", "plan", "subscription"}),
    ("Presentation", {"editing", "thumbnail", "pacing", "camera", "quality", "presentation"}),
)


def _contains(text: str, values: set[str]) -> bool:
    lower = text.lower()
    return any(value in lower for value in values)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def detect_language(text: str) -> str:
    tamil = bool(re.search(r"[\u0b80-\u0bff]", text or ""))
    sinhala = bool(re.search(r"[\u0d80-\u0dff]", text or ""))
    latin = bool(re.search(r"[A-Za-z]", text or ""))
    if tamil and sinhala:
        return "Tamil + Sinhala"
    if tamil and latin:
        return "Tamil + English"
    if sinhala and latin:
        return "Sinhala + English"
    if tamil:
        return "Tamil"
    if sinhala:
        return "Sinhala"
    if latin:
        return "English"
    return "Other"


def _topic(text: str) -> str:
    lower = text.lower()
    for label, terms in TOPIC_RULES:
        if any(term in lower for term in terms):
            return label
    if "?" in text:
        return "Questions"
    return "General feedback"


def classify_comment(comment: dict, duplicate_keys: set[str] | None = None) -> dict:
    """Classify one comment without inventing counts or evidence."""
    text = (comment.get("text") or "").strip()
    normalized = normalize_text(text)
    lower = text.lower()
    positive_hits = sum(1 for word in POSITIVE_WORDS if word in lower)
    negative_hits = sum(1 for word in NEGATIVE_WORDS if word in lower)
    if positive_hits and negative_hits:
        sentiment = "Mixed"
    elif positive_hits > negative_hits:
        sentiment = "Positive"
    elif negative_hits > positive_hits:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    if _contains(text, {"😂", "🤣", "lol", "lmao"}) and ("..." in text or positive_hits):
        emotion = "Sarcastic"
    elif _contains(text, {"excited", "cannot wait", "can't wait", "wow", "amazing"}):
        emotion = "Excited"
    elif _contains(text, {"thank", "grateful", "appreciate"}):
        emotion = "Thankful"
    elif _contains(text, {"confus", "what does", "how do", "why"}) or "?" in text:
        emotion = "Curious" if "?" in text else "Confused"
    elif _contains(text, {"angry", "furious", "hate"}):
        emotion = "Angry"
    elif _contains(text, {"frustrat", "stuck", "not work", "doesn't work"}):
        emotion = "Frustrated"
    elif sentiment == "Positive":
        emotion = "Happy"
    elif sentiment == "Negative":
        emotion = "Disappointed"
    else:
        emotion = "Neutral"

    is_question = "?" in text or bool(re.search(r"\b(how|why|what|where|when|can you|could you)\b", lower))
    if is_question:
        intent = "Question"
    elif _contains(text, {"part 2", "part two", "next video", "please cover", "make a video"}):
        intent = "Requesting Part 2" if "part" in lower else "Requesting another video"
    elif _contains(text, {"buy", "purchase", "pricing", "price", "cost", "subscription"}):
        intent = "Potential customer"
    elif _contains(text, {"suggest", "would love", "you should", "request", "please add"}):
        intent = "Suggestion"
    elif _contains(text, {"thank", "love this", "great video", "awesome video"}):
        intent = "Praise"
    elif _contains(text, SPAM_WORDS) or "http://" in lower or "https://" in lower:
        intent = "Spam"
    elif sentiment == "Negative":
        intent = "Complaint"
    else:
        intent = "Sharing experience"

    toxic = _contains(text, TOXIC_WORDS)
    spam = _contains(text, SPAM_WORDS) or bool(re.search(r"https?://|www\.", lower))
    sarcastic = emotion == "Sarcastic" or bool(re.search(r"\b(sure|great)\s+job\.\.\.", lower))
    duplicate = normalized in (duplicate_keys or set()) and bool(normalized)
    if duplicate:
        spam = True
    if toxic:
        toxicity_severity = "high" if any(word in lower for word in {"threat", "kill", "die"}) else "medium"
    else:
        toxicity_severity = None

    topic = _topic(text)
    if _contains(text, {"beginner", "new to", "starting", "student"}):
        persona = "Beginner / Student"
    elif _contains(text, {"client", "customer", "business", "company", "work"}):
        persona = "Professional / Customer"
    elif _contains(text, {"creator", "channel", "video", "content"}):
        persona = "Content Creator"
    else:
        persona = "General Viewer"

    words = re.findall(r"\w+", text, flags=re.UNICODE)
    quality = 30 + min(35, len(words) * 2)
    quality += min(20, int(comment.get("likes", 0) or 0) * 2)
    quality += min(15, int(comment.get("replies", 0) or 0) * 3)
    if is_question or len(words) >= 12:
        quality += 5
    if spam or toxic:
        quality -= 35
    quality = max(0, min(100, quality))

    evidence = {
        "positive_terms": positive_hits,
        "negative_terms": negative_hits,
        "question": is_question,
        "duplicate": duplicate,
        "contains_url": bool(re.search(r"https?://|www\.", lower)),
    }
    confidence = 0.55
    if positive_hits or negative_hits or is_question:
        confidence += 0.15
    if len(words) >= 8:
        confidence += 0.1
    if spam or toxic:
        confidence += 0.1

    return {
        "language": detect_language(text),
        "sentiment": sentiment,
        "emotion": emotion,
        "topic": topic,
        "intent": intent,
        "persona": persona,
        "cluster": f"{topic} · {intent}",
        "spam": spam,
        "toxic": toxic,
        "toxicity_severity": toxicity_severity,
        "sarcastic": sarcastic,
        "bot_signal": "Likely Automated" if duplicate else ("Suspicious" if spam else "Likely Organic"),
        "quality_score": quality,
        "confidence": min(0.99, confidence),
        "evidence": evidence,
    }


def _percentage(value: int, total: int) -> float:
    return round((value / total * 100) if total else 0.0, 2)


def _distribution(items: list[dict], key: str) -> list[dict]:
    counter = Counter(item.get(key) or "Unknown" for item in items)
    total = len(items)
    return [
        {"label": label, "count": count, "percentage": _percentage(count, total)}
        for label, count in counter.most_common()
    ]


def _examples(comments: list[dict], limit: int = 3) -> list[str]:
    return [(comment.get("text") or "").strip()[:300] for comment in comments[:limit] if (comment.get("text") or "").strip()]


def _group_insights(comments: list[dict], field: str, limit: int = 10) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in comments:
        groups[item.get(field) or "Unknown"].append(item)
    total = len(comments)
    result = []
    for label, group in sorted(groups.items(), key=lambda pair: len(pair[1]), reverse=True)[:limit]:
        result.append({
            "label": label,
            "count": len(group),
            "percentage": _percentage(len(group), total),
            "sentiment": Counter(item.get("sentiment") for item in group).most_common(1)[0][0] if group else "Neutral",
            "confidence": round(mean(item.get("confidence", 0) for item in group), 3) if group else 0,
            "examples": _examples(group),
        })
    return result


def build_report(video: dict, comments: list[dict], analyses: list[dict], previous_report: dict | None = None) -> dict:
    """Build the complete dashboard contract from stored comment evidence."""
    total = len(analyses)
    sentiment_counts = Counter(item.get("sentiment") for item in analyses)
    positive = sentiment_counts.get("Positive", 0)
    negative = sentiment_counts.get("Negative", 0)
    neutral = sentiment_counts.get("Neutral", 0)
    mixed = sentiment_counts.get("Mixed", 0)
    quality_values = [float(item.get("quality_score", 0)) for item in analyses]
    quality_avg = round(mean(quality_values), 2) if quality_values else 0
    spam_count = sum(1 for item in analyses if item.get("spam"))
    toxic_count = sum(1 for item in analyses if item.get("toxic"))
    sarcastic_count = sum(1 for item in analyses if item.get("sarcastic"))
    organic_count = sum(1 for item in analyses if item.get("bot_signal") == "Likely Organic")
    score = round(max(0, min(100, 50 + ((positive - negative) / max(total, 1)) * 50 + (quality_avg - 50) * 0.25 - (toxic_count / max(total, 1)) * 10)), 1)
    score_label = "Strongly Positive" if score >= 75 else "Positive" if score >= 60 else "Mixed" if score >= 45 else "Needs Attention"

    topics = _group_insights(analyses, "topic")
    topic_sentiment = []
    for topic in topics:
        group = [item for item in analyses if item.get("topic") == topic["label"]]
        counts = Counter(item.get("sentiment") for item in group)
        topic_sentiment.append({
            "topic": topic["label"],
            "comment_count": len(group),
            "positive_percentage": _percentage(counts.get("Positive", 0), len(group)),
            "neutral_percentage": _percentage(counts.get("Neutral", 0), len(group)),
            "negative_percentage": _percentage(counts.get("Negative", 0), len(group)),
            "mixed_percentage": _percentage(counts.get("Mixed", 0), len(group)),
        })

    comment_pairs = list(zip(comments, analyses))
    questions = [comment for comment, analysis in comment_pairs if analysis.get("intent") == "Question"]
    complaints = [comment for comment, analysis in comment_pairs if analysis.get("intent") == "Complaint"]
    suggestions = [comment for comment, analysis in comment_pairs if analysis.get("intent") in {"Suggestion", "Requesting Part 2", "Requesting another video"}]
    positive_feedback = [comment for comment, analysis in comment_pairs if analysis.get("sentiment") == "Positive"]
    negative_feedback = [comment for comment, analysis in comment_pairs if analysis.get("sentiment") == "Negative"]

    def evidence_rows(items: list[dict], label: str) -> list[dict]:
        groups = defaultdict(list)
        for comment in items:
            groups[label(comment)].append(comment)
        output = []
        for name, group in sorted(groups.items(), key=lambda pair: len(pair[1]), reverse=True)[:10]:
            output.append({
                "label": name,
                "frequency": len(group),
                "percentage": _percentage(len(group), total),
                "supporting_comments": _examples(group, 5),
                "confidence": round(min(0.99, 0.55 + len(group) / max(total, 1)), 3),
            })
        return output

    question_rows = evidence_rows(questions, lambda item: _topic(item.get("text", "")))
    complaint_rows = evidence_rows(complaints, lambda item: _topic(item.get("text", "")))
    suggestion_rows = evidence_rows(suggestions, lambda item: _topic(item.get("text", "")))
    demand_rows = []
    for row in suggestion_rows[:10]:
        demand = round(min(100, row["frequency"] / max(total, 1) * 100 * 1.5 + min(25, row["frequency"])), 1)
        demand_rows.append({**row, "demand_score": demand, "engagement": sum((item.get("likes", 0) or 0) + (item.get("replies", 0) or 0) for item in suggestions)})
    opportunities = [
        {
            "opportunity": f"Create more content about {row['label']}",
            "demand_score": row["demand_score"],
            "opportunity_score": round(min(100, row["demand_score"] + row["frequency"] * 2), 1),
            "supporting_comments": row["supporting_comments"],
            "reason": "Repeated viewer requests or questions were observed in stored comments.",
            "audience_segment": "Likely audience segment inferred from comment language only",
            "expected_impact": "Higher relevance to demonstrated audience demand",
            "confidence": row["confidence"],
        }
        for row in demand_rows[:5]
    ]
    business_comments = [
        comment for comment, _analysis in comment_pairs
        if _contains(comment.get("text", ""), {"price", "pricing", "cost", "buy", "purchase", "subscription", "plan"})
    ]
    business_groups = defaultdict(list)
    for comment in business_comments:
        business_groups[_topic(comment.get("text", ""))].append(comment)
    business_insights = [
        {
            "signal": label,
            "status": "Observed" if len(group) >= 2 else "Potential",
            "evidence": _examples(group, 5),
            "supporting_comment_count": len(group),
            "confidence": round(min(0.95, 0.55 + len(group) / max(total, 1)), 3),
        }
        for label, group in sorted(business_groups.items(), key=lambda pair: len(pair[1]), reverse=True)
    ]
    reply_candidates = []
    for comment, analysis in sorted(comment_pairs, key=lambda pair: (pair[1].get("intent") == "Question", pair[0].get("likes", 0)), reverse=True):
        if analysis.get("spam") or analysis.get("toxic"):
            continue
        if analysis.get("intent") in {"Question", "Complaint", "Potential customer", "Suggestion"}:
            priority = "HIGH" if analysis.get("intent") in {"Question", "Complaint", "Potential customer"} else "MEDIUM"
            reply_candidates.append({
                "comment_id": comment.get("comment_id"),
                "comment": comment.get("text"),
                "priority": priority,
                "reason": f"{analysis.get('intent')} with {comment.get('likes', 0)} likes and {comment.get('replies', 0)} replies.",
                "engagement": (comment.get("likes", 0) or 0) + (comment.get("replies", 0) or 0),
                "suggested_reply_direction": "Answer the question with a concrete example and invite a follow-up.",
                "confidence": analysis.get("confidence", 0),
            })
        if len(reply_candidates) >= 20:
            break

    engagement = {
        "comment_to_view_ratio": round(total / max(int(video.get("views", 0) or 0), 1), 6),
        "like_to_comment_ratio": round(sum(int(item.get("likes", 0) or 0) for item in comments) / max(total, 1), 3),
        "reply_to_comment_ratio": round(sum(int(item.get("replies", 0) or 0) for item in comments) / max(total, 1), 3),
        "comment_engagement_rate": round((sum(int(item.get("likes", 0) or 0) + int(item.get("replies", 0) or 0) for item in comments) / max(int(video.get("views", 0) or 0), 1)) * 100, 4),
        "average_comment_likes": round(sum(int(item.get("likes", 0) or 0) for item in comments) / max(total, 1), 2),
        "average_replies": round(sum(int(item.get("replies", 0) or 0) for item in comments) / max(total, 1), 2),
    }

    timeline = _build_timeline(comments, analyses)
    summary = {
        "overall_reaction": score_label,
        "what_viewers_loved": f"{positive} comments were classified as positive ({_percentage(positive, total)}%).",
        "main_problem": f"{complaints[0].get('text', '')[:180]}" if complaints else "No recurring complaint reached the evidence threshold.",
        "what_viewers_want": demand_rows[0]["label"] if demand_rows else "No repeated request reached the evidence threshold.",
        "biggest_opportunity": opportunities[0]["opportunity"] if opportunities else "Collect more comments before making a content recommendation.",
        "recommended_action": "Prioritize high-confidence questions and repeated requests, then validate impact in the next run.",
    }

    report = {
        "executive_summary": f"Audience reaction is {score_label.lower()} at {score}/100 based on {total:,} analyzed comments. {summary['recommended_action']}",
        "summary": summary,
        "audience_score": score,
        "audience_score_label": score_label,
        "kpis": {
            "positive_percentage": _percentage(positive, total),
            "neutral_percentage": _percentage(neutral, total),
            "negative_percentage": _percentage(negative, total),
            "mixed_percentage": _percentage(mixed, total),
            "engagement_rate": engagement["comment_engagement_rate"],
            "average_comment_quality": quality_avg,
        },
        "sentiment": _distribution(analyses, "sentiment"),
        "emotions": _distribution(analyses, "emotion"),
        "languages": _distribution(analyses, "language"),
        "top_topics": topics,
        "topic_sentiment": topic_sentiment,
        "questions": question_rows,
        "complaints": complaint_rows,
        "pain_points": [{**row, "severity": "Medium", "impact": "Repeated viewer friction", "recommended_action": "Address the topic in a follow-up or documentation."} for row in complaint_rows],
        "suggestions": suggestion_rows,
        "positive_feedback": evidence_rows(positive_feedback, lambda item: _topic(item.get("text", ""))),
        "negative_feedback": evidence_rows(negative_feedback, lambda item: _topic(item.get("text", ""))),
        "audience_intent": _distribution(analyses, "intent"),
        "audience_personas": _distribution(analyses, "persona"),
        "comment_clusters": _group_insights(analyses, "cluster"),
        "comment_quality": {
            "average": quality_avg,
            "distribution": [{"label": label, "count": count, "percentage": _percentage(count, total)} for label, count in Counter("High" if value >= 75 else "Medium" if value >= 45 else "Low" for value in quality_values).most_common()],
            "high_value_comments": _examples([comment for comment, analysis in comment_pairs if analysis.get("quality_score", 0) >= 75], 10),
        },
        "spam_analysis": {"spam_count": spam_count, "spam_percentage": _percentage(spam_count, total), "spam_categories": _distribution([item for item in analyses if item.get("spam")], "intent")},
        "bot_analysis": {"organic_count": organic_count, "organic_percentage": _percentage(organic_count, total), "suspicious_count": total - organic_count, "signals": _distribution(analyses, "bot_signal")},
        "toxicity": {"toxic_count": toxic_count, "toxic_percentage": _percentage(toxic_count, total), "severity": _distribution([item for item in analyses if item.get("toxic")], "toxicity_severity")},
        "sarcasm": {"sarcastic_count": sarcastic_count, "sarcastic_percentage": _percentage(sarcastic_count, total)},
        "engagement": engagement,
        "timeline": timeline,
        "audience_demand": demand_rows,
        "content_opportunities": opportunities,
        "next_video_recommendations": [{"video_idea": item["opportunity"], **{key: item[key] for key in ("demand_score", "opportunity_score", "supporting_comments", "reason", "audience_segment", "confidence")}} for item in opportunities],
        "reply_opportunities": reply_candidates,
        "priority_actions": [{"priority": "HIGH", "action": f"Address repeated audience demand around {item['label']}", "reason": "The topic/request appears repeatedly in stored comments.", "evidence": item["supporting_comments"], "supporting_comment_count": item["frequency"], "expected_impact": "High relevance to observed audience demand", "confidence": item["confidence"]} for item in demand_rows[:5]],
        "business_insights": business_insights,
        "creator_recommendations": [summary["recommended_action"]],
        "historical_comparison": _compare_reports(
            previous_report,
            score,
            report_kpis={"positive_percentage": _percentage(positive, total), "negative_percentage": _percentage(negative, total)},
            current_topics=[item.get("label") for item in topics],
            current_demand=[item.get("label") for item in demand_rows],
        ),
        "confidence": {"overall": round(mean(item.get("confidence", 0) for item in analyses), 3) if analyses else 0, "uncertain_when_below": 0.6},
        "failed_batches": [],
        "video": _json_safe(video),
        "analysis_metadata": {"comments_analyzed": total, "source": "stored YouTube comments", "deterministic_metrics": True},
    }
    return report


def _build_timeline(comments: list[dict], analyses: list[dict]) -> list[dict]:
    dated = []
    for comment, analysis in zip(comments, analyses):
        published_at = _coerce_datetime(comment.get("published_at"))
        if published_at:
            dated.append((comment, analysis, published_at))
    if not dated:
        return []
    dates = [item[2] for item in dated]
    span_days = max(1, (max(dates) - min(dates)).days)
    bucket = "hour" if span_days <= 2 else "day" if span_days <= 45 else "week"
    groups = defaultdict(list)
    for comment, analysis, dt in dated:
        if bucket == "hour":
            key = dt.replace(minute=0, second=0, microsecond=0).isoformat()
        elif bucket == "day":
            key = dt.date().isoformat()
        else:
            key = f"{dt.isocalendar().year}-W{dt.isocalendar().week:02d}"
        groups[key].append((comment, analysis))
    return [{
        "bucket": key,
        "granularity": bucket,
        "comment_volume": len(group),
        "positive": sum(1 for _, item in group if item.get("sentiment") == "Positive"),
        "negative": sum(1 for _, item in group if item.get("sentiment") == "Negative"),
        "engagement": sum((comment.get("likes", 0) or 0) + (comment.get("replies", 0) or 0) for comment, _ in group),
    } for key, group in sorted(groups.items())]


def _coerce_datetime(value):
    """Normalize model datetimes and serialized ISO timestamps before arithmetic."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
        except ValueError:
            return None
    return None


def _json_safe(value):
    """Convert report values to primitives accepted by SQLAlchemy JSON columns."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


def _compare_reports(previous: dict | None, score: float, report_kpis: dict, current_topics: list[str], current_demand: list[str]) -> dict:
    if not previous:
        return {"available": False, "message": "A comparison will appear after the next analysis run."}
    previous_kpis = previous.get("kpis", {}) if isinstance(previous, dict) else {}
    previous_score = float(previous.get("audience_score", 0) or 0)
    previous_topics = [item.get("label") for item in (previous.get("top_topics", []) if isinstance(previous, dict) else [])]
    previous_demand = [item.get("label") for item in (previous.get("audience_demand", []) if isinstance(previous, dict) else [])]
    return {
        "available": True,
        "previous_audience_score": previous_score,
        "current_audience_score": score,
        "audience_score_delta": round(score - previous_score, 1),
        "positive_percentage_delta": round(report_kpis["positive_percentage"] - float(previous_kpis.get("positive_percentage", 0) or 0), 2),
        "negative_percentage_delta": round(report_kpis["negative_percentage"] - float(previous_kpis.get("negative_percentage", 0) or 0), 2),
        "topics_added": [topic for topic in current_topics if topic not in previous_topics],
        "topics_removed": [topic for topic in previous_topics if topic not in current_topics],
        "demand_added": [item for item in current_demand if item not in previous_demand],
        "demand_removed": [item for item in previous_demand if item not in current_demand],
    }


def safe_ai_payload(comments: list[dict], report: dict) -> dict:
    """Create a bounded, evidence-only payload for optional AI narrative enrichment."""
    ranked = sorted(zip(comments, report.get("comment_clusters", [])), key=lambda pair: (pair[0].get("likes", 0), len(pair[0].get("text", ""))), reverse=True)
    excerpts = [item[0].get("text", "")[:400] for item in ranked[:60] if item[0].get("text")]
    return {
        "video": report.get("video", {}),
        "kpis": report.get("kpis", {}),
        "top_topics": report.get("top_topics", [])[:10],
        "questions": report.get("questions", [])[:10],
        "complaints": report.get("complaints", [])[:10],
        "demand": report.get("audience_demand", [])[:10],
        "comment_excerpts": excerpts,
    }
