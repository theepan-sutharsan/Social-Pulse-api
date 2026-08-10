"""Optional provider-backed narrative enrichment for audience reports."""
from __future__ import annotations

import json
import re
import time

import requests
from flask import current_app

from app.services.audience_intelligence_service import safe_ai_payload


class AudienceAIError(Exception):
    pass


ALLOWED_NARRATIVE_KEYS = {
    "executive_summary",
    "summary",
    "creator_recommendations",
    "business_insights",
    "priority_actions",
    "next_video_recommendations",
}


def _parse_json(text: str) -> dict:
    cleaned = (text or "").strip().replace("```json", "").replace("```", "").strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise AudienceAIError("AI returned invalid JSON.")
        value = json.loads(match.group())
    if not isinstance(value, dict):
        raise AudienceAIError("AI response must be a JSON object.")
    return value


def _classification_prompt(comments: list[dict]) -> str:
    schema = {
        "comments": [{
            "comment_id": "",
            "language": "",
            "sentiment": "Positive|Neutral|Negative|Mixed",
            "emotion": "",
            "topic": "",
            "intent": "",
            "persona": "",
            "cluster": "",
            "spam": False,
            "toxic": False,
            "toxicity_severity": None,
            "sarcastic": False,
            "bot_signal": "Likely Organic|Suspicious|Likely Automated",
            "quality_score": 0,
            "confidence": 0.0,
            "evidence": {},
        }]
    }
    return f"""Classify every supplied YouTube comment using only its text and metadata. Return ONLY valid JSON in this shape:
{json.dumps(schema, ensure_ascii=False)}
Do not invent comments or counts. Preserve every supplied comment_id exactly. Use low confidence when uncertain, and keep toxicity separate from sentiment and spam.

Comments:
{json.dumps(comments, ensure_ascii=False, indent=2)}"""


def _validate_batch(value: dict, expected_ids: set[str]) -> dict[str, dict]:
    rows = value.get("comments") if isinstance(value, dict) else None
    if not isinstance(rows, list):
        raise AudienceAIError("AI batch response did not contain a comments array.")
    required = {"comment_id", "language", "sentiment", "emotion", "topic", "intent", "persona", "cluster", "spam", "toxic", "sarcastic", "quality_score", "confidence"}
    result = {}
    for row in rows:
        if not isinstance(row, dict) or str(row.get("comment_id")) not in expected_ids:
            continue
        if not required.issubset(row):
            raise AudienceAIError("AI batch response was missing a required classification field.")
        confidence = float(row.get("confidence", 0))
        quality = float(row.get("quality_score", 0))
        result[str(row["comment_id"])] = {
            **row,
            "comment_id": str(row["comment_id"]),
            "spam": bool(row.get("spam")),
            "toxic": bool(row.get("toxic")),
            "sarcastic": bool(row.get("sarcastic")),
            # These fields are requested in the prompt but are optional in
            # real provider responses. Normalize them here so the worker can
            # persist every valid classification without raising KeyError.
            "toxicity_severity": row.get("toxicity_severity"),
            "bot_signal": row.get("bot_signal") or (
                "Suspicious" if row.get("spam") else "Likely Organic"
            ),
            "quality_score": max(0, min(100, quality)),
            "confidence": max(0, min(0.99, confidence)),
            "evidence": row.get("evidence") if isinstance(row.get("evidence"), dict) else {},
        }
    if set(result) != expected_ids:
        raise AudienceAIError("AI batch response did not classify every supplied comment.")
    return result


def classify_batch_with_ai(comments: list[dict], provider: str = "auto") -> tuple[dict[str, dict], str]:
    """Classify one bounded batch with a configured provider, retrying bad batches."""
    if not comments:
        return {}, "deterministic"
    google_key = current_app.config.get("GOOGLE_API_KEY", "") or current_app.config.get("GEMINI_API_KEY", "")
    claude_key = current_app.config.get("ANTHROPIC_API_KEY", "")
    targets = [provider] if provider in {"gemini", "claude"} else ["gemini", "claude"]
    expected_ids = {str(item.get("comment_id")) for item in comments}
    prompt = _classification_prompt(comments)
    for target in targets:
        key = google_key if target == "gemini" else claude_key
        if not key or key.lower().startswith("your-"):
            continue
        for attempt in range(3):
            try:
                value = _gemini(prompt, key) if target == "gemini" else _claude(prompt, key)
                return _validate_batch(value, expected_ids), target
            except Exception:
                if attempt < 2:
                    time.sleep(2 ** attempt)
    return {}, "deterministic"


def _prompt(payload: dict) -> str:
    return f"""You are a careful audience-intelligence editor. Use only the supplied evidence.
Do not invent comments, counts, opinions, causes, or business opportunities. Deterministic
metrics are already calculated and must not be changed. Return ONLY valid JSON with these
optional keys: executive_summary (string), summary (object with the same keys supplied),
creator_recommendations (array), business_insights (array), priority_actions (array),
next_video_recommendations (array). Every recommendation must mention the evidence label or
comment count it relies on; use 'Uncertain' when evidence is weak.

Evidence payload:
{json.dumps(payload, ensure_ascii=False, indent=2)}"""


def _gemini(prompt: str, key: str) -> dict:
    base = current_app.config.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    model = current_app.config.get("GEMINI_MODEL", "gemini-flash-latest")
    response = requests.post(
        f"{base}/models/{model}:generateContent?key={key}",
        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}},
        timeout=45,
    )
    if response.status_code != 200:
        raise AudienceAIError("Gemini enrichment failed.")
    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return _parse_json(text)


def _claude(prompt: str, key: str) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=key)
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=3000,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json(message.content[0].text)


def enrich_report(report: dict, comments: list[dict], provider: str = "auto") -> tuple[dict, str]:
    """Enrich narratives when a provider is configured; deterministic report is never replaced."""
    google_key = current_app.config.get("GOOGLE_API_KEY", "") or current_app.config.get("GEMINI_API_KEY", "")
    claude_key = current_app.config.get("ANTHROPIC_API_KEY", "")
    prompt = _prompt(safe_ai_payload(comments, report))
    targets = [provider] if provider in {"gemini", "claude"} else ["gemini", "claude"]
    errors = []
    for target in targets:
        try:
            if target == "gemini" and google_key and not google_key.lower().startswith("your-"):
                value = _gemini(prompt, google_key)
            elif target == "claude" and claude_key and not claude_key.lower().startswith("your-"):
                value = _claude(prompt, claude_key)
            else:
                continue
            merged = dict(report)
            for key in ALLOWED_NARRATIVE_KEYS:
                if key in value and isinstance(value[key], type(report.get(key))) and value[key] is not None:
                    merged[key] = value[key]
            merged["ai_enrichment"] = {"provider": target, "status": "completed", "evidence_only": True}
            return merged, target
        except Exception as exc:  # provider failures must not erase deterministic results
            errors.append(str(exc))
    result = dict(report)
    result["ai_enrichment"] = {"provider": None, "status": "deterministic_only", "evidence_only": True, "errors": errors[-2:]}
    return result, "deterministic"
