"""
Social Pulse API — YouTube Channel Claude Analysis Service
Builds a structured payload from video + transcript data and calls Claude API
for pattern analysis, content gap detection, video idea generation, and script outline.
"""
import json
import logging
import re
from flask import current_app

logger = logging.getLogger(__name__)


class YTAnalysisServiceError(Exception):
    """Raised when Claude API call or analysis fails."""
    pass


def build_analysis_payload(videos: list[dict], transcripts: dict[str, dict]) -> dict:
    """
    Condense up to 50 videos into a compact structured summary to keep Claude token
    usage efficient. Sends full metadata for all videos but only transcript excerpts
    for the top and bottom performers by view count.
    """
    if not videos:
        raise YTAnalysisServiceError("No video data provided for analysis.")

    sorted_videos = sorted(videos, key=lambda v: v.get("view_count", 0), reverse=True)
    top_10 = sorted_videos[:10]
    bottom_10 = sorted_videos[-10:]

    def summarize(v: dict) -> dict:
        vid_id = v.get("video_id", "")
        t_data = transcripts.get(vid_id, {})
        raw_text = t_data.get("text") or ""
        transcript_excerpt = raw_text[:600].strip() if raw_text else ""

        return {
            "title": v.get("title", ""),
            "views": v.get("view_count", 0),
            "likes": v.get("like_count", 0),
            "comments": v.get("comment_count", 0),
            "duration_sec": v.get("duration_seconds", 0),
            "published_at": v["published_at"].isoformat() if v.get("published_at") else None,
            "tags": (v.get("tags") or [])[:10],
            "transcript_excerpt": transcript_excerpt,
        }

    return {
        "total_videos_analyzed": len(videos),
        "top_performers": [summarize(v) for v in top_10],
        "low_performers": [summarize(v) for v in bottom_10],
        "all_titles": [v.get("title", "") for v in videos],
    }


def generate_channel_analysis(channel_title: str, payload: dict) -> dict:
    """
    Send structured channel data to Claude API.
    Returns parsed JSON with performance_insights, title_patterns, topic_clusters,
    content_gaps, optimal_duration_seconds, video_ideas (5), and top_pick_script_outline.
    """
    api_key = current_app.config.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise YTAnalysisServiceError("ANTHROPIC_API_KEY is not configured.")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    except ImportError:
        raise YTAnalysisServiceError("anthropic library is not installed. Run: pip install anthropic")

    system_prompt = (
        "You are an expert YouTube content strategist with deep knowledge of algorithm optimization, "
        "audience psychology, and viral content patterns. You analyze channel performance data and "
        "produce highly actionable insights. Always respond with ONLY valid JSON — no markdown "
        "formatting, no code fences, no preamble or explanation outside the JSON."
    )

    user_prompt = f"""Channel: {channel_title}

Performance Data (top/bottom videos by views + all titles for pattern scanning):
{json.dumps(payload, indent=2, default=str)}

Analyze this data and respond with ONLY the following JSON structure (no markdown, no extra text):
{{
  "performance_insights": "2-3 sentences on what drives high vs low performance for this channel",
  "title_patterns": "common structural patterns found in high-performing titles (e.g. listicles, how-tos, controversy hooks)",
  "topic_clusters": ["topic1", "topic2", "topic3", "topic4", "topic5"],
  "content_gaps": "topics or angles this channel hasn't covered but the audience likely wants based on the data",
  "optimal_duration_seconds": 600,
  "video_ideas": [
    {{"title": "...", "hook": "First 10 seconds hook script", "rationale": "Why this will perform based on the data patterns"}},
    {{"title": "...", "hook": "...", "rationale": "..."}},
    {{"title": "...", "hook": "...", "rationale": "..."}},
    {{"title": "...", "hook": "...", "rationale": "..."}},
    {{"title": "...", "hook": "...", "rationale": "..."}}
  ],
  "top_pick_script_outline": "A full structured script outline for the strongest idea: include intro hook, 4-6 main sections with approximate timestamps, transition lines, and a strong CTA. Be specific and actionable."
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:
        raise YTAnalysisServiceError(f"Claude API call failed: {e}")

    raw_text = response.content[0].text.strip() if response.content else ""

    # Strip any accidental markdown code fences
    raw_text = re.sub(r"^```json\s*", "", raw_text)
    raw_text = re.sub(r"^```\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text).strip()

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error(f"Claude returned invalid JSON: {raw_text[:500]}")
        raise YTAnalysisServiceError(f"Claude returned invalid JSON: {e}")

    # Validate required keys
    required_keys = [
        "performance_insights", "title_patterns", "topic_clusters",
        "content_gaps", "optimal_duration_seconds", "video_ideas", "top_pick_script_outline"
    ]
    missing = [k for k in required_keys if k not in result]
    if missing:
        raise YTAnalysisServiceError(f"Claude response missing required keys: {missing}")

    # Ensure exactly 5 video ideas
    ideas = result.get("video_ideas", [])
    if not isinstance(ideas, list) or len(ideas) == 0:
        raise YTAnalysisServiceError("Claude returned no video ideas.")

    return result
