"""
Social Pulse API — YouTube Channel AI Analysis Service
Supports multiple AI providers: Claude (Anthropic) and Gemini (Google).

New analysis schema: per-video individual breakdown + overall channel insights.
Every video in the list is analyzed — no skipping.
"""
import json
import logging
import re
import requests as _requests
from flask import current_app

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = ("gemini", "claude")


class YTAnalysisServiceError(Exception):
    """Raised when an AI API call or analysis fails."""
    pass


# ─── Payload builder ─────────────────────────────────────────────────────────

def build_analysis_payload(videos: list[dict], transcripts: dict[str, dict]) -> dict:
    """
    Build a comprehensive payload of ALL videos for per-video AI analysis.
    Every video is included with full metadata + transcript excerpt.
    Videos are the most recent N uploads (newest first from YouTube uploads playlist).
    """
    if not videos:
        raise YTAnalysisServiceError("No video data provided for analysis.")

    def build_video_entry(v: dict) -> dict:
        vid_id = v.get("video_id", "")
        t_data = transcripts.get(vid_id, {})
        raw_text = t_data.get("text") or ""
        transcript_excerpt = raw_text[:800].strip() if raw_text else ""

        views = v.get("view_count", 0)
        likes = v.get("like_count", 0)
        comments = v.get("comment_count", 0)
        # Engagement rate: (likes + comments) / views * 100, capped reasonably
        engagement_rate = round((likes + comments) / views * 100, 2) if views > 0 else 0.0

        return {
            "video_id": vid_id,
            "title": v.get("title", ""),
            "url": f"https://www.youtube.com/watch?v={vid_id}",
            "published_at": v["published_at"].isoformat() if v.get("published_at") else None,
            "duration_sec": v.get("duration_seconds", 0),
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement_rate_pct": engagement_rate,
            "tags": (v.get("tags") or [])[:10],
            "transcript_excerpt": transcript_excerpt,
        }

    video_entries = [build_video_entry(v) for v in videos]

    return {
        "total_videos": len(videos),
        "note": (
            f"These are the {len(videos)} most recent uploads from the channel, "
            "ordered newest-first. Analyze EVERY video individually."
        ),
        "videos": video_entries,
    }


# ─── Shared helpers ──────────────────────────────────────────────────────────

def _build_prompts(channel_title: str, payload: dict) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for any provider."""
    system_prompt = (
        "You are an expert YouTube channel analyst with deep knowledge of "
        "algorithm optimization, audience psychology, SEO, thumbnail design, "
        "and viral content patterns. "
        "You analyze EVERY video provided — you never skip any. "
        "Always respond with ONLY valid JSON — no markdown, no code fences, "
        "no preamble or explanation outside the JSON object."
    )

    user_prompt = f"""You are an expert YouTube channel analyst.

Channel: {channel_title}

Analyze ALL the provided videos below. The list contains {payload['total_videos']} videos.
{payload['note']}

IMPORTANT INSTRUCTIONS:
- Analyze EVERY video in the list. Do NOT skip any.
- Do NOT select only top-performing videos.
- Generate an individual analysis for EACH video.
- Compare all videos together and provide overall channel insights.

Video Data:
{json.dumps(payload['videos'], indent=2, default=str)}

For each video analyze:
1. Title quality (score 1-10)
2. Thumbnail quality (score 1-10, based on title/topic context since image not provided)
3. SEO optimization (score 1-10, based on title keywords and tags)
4. Content quality (score 1-10, based on transcript and engagement signals)
5. Audience engagement analysis
6. Strengths (list)
7. Weaknesses (list)
8. Improvement suggestions (list)

After analyzing ALL videos, provide overall channel insights AND top 5 content suggestions with a complete script outline for the top pick.

Respond with ONLY this exact JSON structure (no markdown, no extra text):
{{
  "total_videos_analyzed": {payload['total_videos']},
  "video_analysis": [
    {{
      "video_id": "",
      "title": "",
      "url": "",
      "published_at": "",
      "views": 0,
      "likes": 0,
      "comments": 0,
      "engagement_rate_pct": 0.0,
      "analysis": {{
        "title_score": 0,
        "thumbnail_score": 0,
        "seo_score": 0,
        "content_score": 0,
        "overall_score": 0.0,
        "engagement_analysis": "",
        "strengths": [],
        "weaknesses": [],
        "suggestions": []
      }}
    }}
  ],
  "overall_channel_insights": {{
    "best_performing_videos": [],
    "lowest_performing_videos": [],
    "top_patterns": [],
    "common_problems": [],
    "content_category_performance": "",
    "audience_behavior_insights": "",
    "recommended_content_strategy": "",
    "future_video_ideas": [],
    "seo_improvement_suggestions": [],
    "thumbnail_improvement_suggestions": [],
    "recommendations": []
  }},
  "top_5_content_suggestions": [
    {{"title": "Idea 1 title", "hook": "First 10 seconds hook script", "rationale": "Why this idea will perform well based on channel data"}},
    {{"title": "Idea 2 title", "hook": "...", "rationale": "..."}},
    {{"title": "Idea 3 title", "hook": "...", "rationale": "..."}},
    {{"title": "Idea 4 title", "hook": "...", "rationale": "..."}},
    {{"title": "Idea 5 title", "hook": "...", "rationale": "..."}}
  ],
  "top_pick_script_outline": "Detailed, step-by-step script outline for Idea 1 (including hook, main points with timestamps, transitions, call to action)."
}}

The video_analysis array MUST contain exactly {payload['total_videos']} items — one for every video provided.
Analyze ALL of them completely."""

    return system_prompt, user_prompt


def _clean_json(raw_text: str) -> str:
    """Strip accidental markdown code fences from the response."""
    raw_text = re.sub(r"^```json\s*", "", raw_text, flags=re.MULTILINE)
    raw_text = re.sub(r"^```\s*", "", raw_text, flags=re.MULTILINE)
    raw_text = re.sub(r"\s*```$", "", raw_text.strip())
    return raw_text.strip()


def _validate_result(result: dict, provider_name: str, expected_count: int) -> dict:
    """Validate that the AI response contains all required keys and video count."""
    required_keys = ["total_videos_analyzed", "video_analysis", "overall_channel_insights"]
    missing = [k for k in required_keys if k not in result]
    if missing:
        raise YTAnalysisServiceError(
            f"{provider_name} response missing required keys: {missing}"
        )

    video_analysis = result.get("video_analysis", [])
    if not isinstance(video_analysis, list) or len(video_analysis) == 0:
        raise YTAnalysisServiceError(
            f"{provider_name} returned no video analysis entries."
        )

    if len(video_analysis) < expected_count:
        logger.warning(
            f"{provider_name} returned {len(video_analysis)}/{expected_count} video analyses. "
            "Some videos may have been skipped by the model."
        )

    return result


def _parse_result(raw: str, provider_name: str, expected_count: int) -> dict:
    """Parse and validate a provider response before accepting it."""
    cleaned = _clean_json(raw)
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise YTAnalysisServiceError(
                f"Failed to parse JSON response from {provider_name}."
            )
        try:
            result = json.loads(match.group())
        except (TypeError, json.JSONDecodeError) as exc:
            raise YTAnalysisServiceError(
                f"Failed to parse JSON response from {provider_name}."
            ) from exc

    return _validate_result(result, provider_name, expected_count)


# ─── Claude provider ─────────────────────────────────────────────────────────

def _call_claude(system_prompt: str, user_prompt: str) -> str:
    """Call Anthropic Claude API and return the raw response text."""
    api_key = current_app.config.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise YTAnalysisServiceError("ANTHROPIC_API_KEY is not configured.")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    except ImportError:
        raise YTAnalysisServiceError(
            "anthropic library is not installed. Run: pip install anthropic"
        )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:
        raise YTAnalysisServiceError(f"Claude API call failed: {e}")

    return response.content[0].text.strip() if response.content else ""


# ─── Gemini provider ─────────────────────────────────────────────────────────

def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    """
    Call Google Gemini API via direct REST (no SDK required).
    Falls back through model names: configured model → gemini-2.0-flash → gemini-1.5-flash.
    """
    api_key = current_app.config.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise YTAnalysisServiceError(
            "GOOGLE_API_KEY is not configured. Add it to your .env file."
        )

    base_url = current_app.config.get(
        "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
    ).rstrip("/")
    model = current_app.config.get("GEMINI_MODEL", "gemini-2.0-flash")

    headers = {"Content-Type": "application/json"}
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
        },
    }

    models_to_try = [model, "gemini-2.0-flash", "gemini-1.5-flash"]
    seen: set[str] = set()
    last_error = None

    for m in models_to_try:
        if m in seen:
            continue
        seen.add(m)
        url = f"{base_url}/models/{m}:generateContent?key={api_key}"
        try:
            res = _requests.post(url, headers=headers, json=payload, timeout=120)
            if res.status_code == 200:
                data = res.json()
                raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return raw
            last_error = f"HTTP {res.status_code}: {res.text[:300]}"
            logger.warning(f"Gemini model '{m}' returned {res.status_code}, trying next...")
        except Exception as e:
            safe_error = str(e).replace(api_key, "[redacted]")
            last_error = safe_error
            logger.warning("Gemini model '%s' request failed: %s", m, safe_error)

    raise YTAnalysisServiceError(
        f"Gemini API call failed after all fallbacks. Last error: {last_error}"
    )


# ─── Public entry point ───────────────────────────────────────────────────────

def generate_channel_analysis(
    channel_title: str,
    payload: dict,
    provider: str = "gemini",
) -> tuple[dict, str]:
    """
    Send structured channel data to the selected AI provider.
    Returns parsed JSON with:
      - total_videos_analyzed
      - video_analysis: per-video breakdown for EVERY video
      - overall_channel_insights: patterns, problems, recommendations
    """
    provider = provider.lower().strip()
    if provider not in SUPPORTED_PROVIDERS:
        raise YTAnalysisServiceError(
            f"Unsupported provider '{provider}'. Choose from: {SUPPORTED_PROVIDERS}"
        )

    expected_count = payload.get("total_videos", 0)
    system_prompt, user_prompt = _build_prompts(channel_title, payload)

    provider_order = [provider] + [p for p in SUPPORTED_PROVIDERS if p != provider]
    errors: list[str] = []

    for candidate in provider_order:
        try:
            raw = (
                _call_gemini(system_prompt, user_prompt)
                if candidate == "gemini"
                else _call_claude(system_prompt, user_prompt)
            )
            result = _parse_result(raw, candidate, expected_count)
            return result, candidate
        except Exception as exc:
            safe_error = str(exc)
            errors.append(f"{candidate}: {safe_error}")
            logger.warning(
                "Channel analysis provider '%s' failed; trying fallback: %s",
                candidate,
                safe_error,
            )

    raise YTAnalysisServiceError(
        "All configured AI providers failed. " + " | ".join(errors)
    )
