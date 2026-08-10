"""
Social Pulse API — Enhanced AI Client
Added: content_calendar generation, hashtag research, posting_time analysis.
"""
import json
from flask import current_app

SUGGESTION_TYPE_INSTRUCTIONS = {
    "title": (
        "Generate 5 compelling, SEO-optimized video title ideas that are highly clickable "
        "and match the content patterns below. Each title should be under 70 characters. "
        "Return JSON: {\"titles\": [\"Title 1\", ..., \"Title 5\"], \"reasoning\": \"...\", \"seo_tips\": \"...\"}"
    ),
    "caption": (
        "Write 3 engaging social media captions (short=<100 chars, medium=<300 chars, long=<600 chars) "
        "optimized for the platform patterns below. Include relevant emojis. "
        "Return JSON: {\"captions\": [{\"length\": \"short\", \"text\": \"...\", \"character_count\": N}, ...]}"
    ),
    "hook": (
        "Generate 5 powerful video hook lines for the first 5-10 seconds "
        "that instantly capture viewer attention and create curiosity. "
        "Return JSON: {\"hooks\": [\"Hook 1\", ..., \"Hook 5\"], \"hook_types\": [\"curiosity\", \"stat\", ...], \"reasoning\": \"...\"}"
    ),
    "hashtag": (
        "Suggest 20 highly relevant hashtags grouped by category (trending, niche, branded) "
        "based on the content patterns below. Also suggest 5 hashtags to avoid. "
        "Return JSON: {\"hashtags\": [\"#tag1\", ...], \"categories\": {\"trending\": [...], \"niche\": [...], \"branded\": [...]}, \"avoid\": [...]}"
    ),
    "thumbnail_concept": (
        "Describe 3 detailed thumbnail concepts (colors, text overlay, composition, emotion, contrast) "
        "that would maximize click-through rate for this content niche. "
        "Return JSON: {\"concepts\": [{\"title\": \"...\", \"description\": \"...\", \"colors\": [...], \"text_overlay\": \"...\", \"emotion\": \"...\", \"ctr_score\": N}]}"
    ),
    "posting_time": (
        "Based on these video performance patterns, recommend the top 3 posting windows "
        "with day, time, timezone, and detailed reasoning. Also suggest content frequency. "
        "Return JSON: {\"recommendations\": [{\"day\": \"...\", \"time\": \"...\", \"timezone\": \"EST\", \"reason\": \"...\", \"expected_boost\": \"...\"}], \"frequency\": \"...\"}"
    ),
    "content_calendar": (
        "Create a 4-week content calendar with topic ideas, formats, posting schedule, "
        "and estimated performance notes based on these patterns. "
        "Return JSON: {\"weeks\": [{\"week\": 1, \"theme\": \"...\", \"posts\": [{\"day\": \"...\", \"topic\": \"...\", \"format\": \"...\", \"duration\": \"...\", \"note\": \"...\"}]}]}"
    ),
}


def _build_prompt(suggestion_type: str, videos: list, account_name: str = "") -> str:
    instruction = SUGGESTION_TYPE_INSTRUCTIONS.get(
        suggestion_type,
        "Generate a content suggestion based on these patterns."
    )
    top_videos = sorted(videos, key=lambda v: v.get("views", 0), reverse=True)[:10]
    pattern_lines = []
    for i, v in enumerate(top_videos, 1):
        tags = ", ".join((v.get("tags") or [])[:5]) or "none"
        duration_min = f"{v.get('duration_seconds', 0) // 60}m" if v.get("duration_seconds") else "unknown"
        pattern_lines.append(
            f"{i}. \"{v.get('title', 'No title')}\" | "
            f"Views: {v.get('views', 0):,} | "
            f"Likes: {v.get('likes', 0):,} | "
            f"Comments: {v.get('comments', 0):,} | "
            f"Engagement: {v.get('engagement_rate', 0):.2f}% | "
            f"Duration: {duration_min} | "
            f"Tags: {tags}"
        )
    patterns_text = "\n".join(pattern_lines) if pattern_lines else "No videos available yet."
    account_line = f"Channel/Account: {account_name}\n" if account_name else ""

    # Compute some aggregate insights
    if top_videos:
        avg_views = sum(v.get("views", 0) for v in top_videos) // max(len(top_videos), 1)
        avg_eng = sum(v.get("engagement_rate", 0) for v in top_videos) / max(len(top_videos), 1)
        duration_most_common = max(set(
            "short (<5m)" if (v.get("duration_seconds") or 0) < 300 else
            "medium (5-15m)" if (v.get("duration_seconds") or 0) < 900 else "long (15m+)"
            for v in top_videos
        ), key=lambda x: [
            "short (<5m)" if (v.get("duration_seconds") or 0) < 300 else
            "medium (5-15m)" if (v.get("duration_seconds") or 0) < 900 else "long (15m+)"
            for v in top_videos
        ].count(x))
        insights = (
            f"\nInsights: Avg views={avg_views:,} | Avg engagement={avg_eng:.2f}% | "
            f"Best performing duration={duration_most_common}"
        )
    else:
        insights = ""

    prompt = (
        f"You are an expert social media growth strategist for Social Pulse.\n\n"
        f"{account_line}"
        f"Task: {instruction}\n"
        f"{insights}\n\n"
        f"Top performing videos/posts (sorted by views):\n{patterns_text}\n\n"
        f"Provide ONLY valid JSON as your response. No markdown code blocks, no explanation outside the JSON."
    )
    return prompt


class AIProviderError(Exception):
    """Custom exception raised when AI provider generation fails or keys are unconfigured."""
    pass


def _generate_gemini_suggestion(prompt: str, api_key: str, suggestion_type: str, account_name: str) -> dict:
    import requests
    base_url = current_app.config.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    model = current_app.config.get("GEMINI_MODEL", "gemini-flash-latest")
    
    url = f"{base_url}/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "responseMimeType": "application/json"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code != 200 and model != "gemini-1.5-flash":
            url_fallback = f"{base_url}/models/gemini-1.5-flash:generateContent?key={api_key}"
            response = requests.post(url_fallback, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            err_detail = response.json().get("error", {}).get("message", response.text)
            raise AIProviderError(f"Google Gemini API error ({response.status_code}): {err_detail}")
        
        res_data = response.json()
        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            import re
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return {"raw": raw_text}
    except AIProviderError:
        raise
    except Exception as e:
        raise AIProviderError(f"Google Gemini API request failed: {str(e)}")


def _generate_claude_suggestion(prompt: str, api_key: str, suggestion_type: str, account_name: str) -> dict:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text.strip()
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            import re
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return {"raw": raw_text}
    except Exception as e:
        raise AIProviderError(f"Anthropic Claude API request failed: {str(e)}")


def generate_suggestion(suggestion_type: str, videos: list, account_name: str = "", provider: str = None) -> dict:
    google_key = current_app.config.get("GOOGLE_API_KEY", "") or current_app.config.get("GEMINI_API_KEY", "")
    anthropic_key = current_app.config.get("ANTHROPIC_API_KEY", "")
    prompt = _build_prompt(suggestion_type, videos, account_name)

    target_provider = (provider or "").lower()

    if target_provider == "stub":
        return _stub_suggestion(suggestion_type, account_name)

    if target_provider == "gemini":
        if not google_key or google_key in ["your-google-api-key", "your-gemini-api-key"]:
            raise AIProviderError("Google Gemini API key is not configured. Please set GOOGLE_API_KEY in your api/.env file.")
        return _generate_gemini_suggestion(prompt, google_key, suggestion_type, account_name)

    if target_provider == "claude":
        if not anthropic_key or anthropic_key == "your-anthropic-api-key":
            raise AIProviderError("Anthropic Claude API key is not configured. Please set ANTHROPIC_API_KEY in your api/.env file.")
        return _generate_claude_suggestion(prompt, anthropic_key, suggestion_type, account_name)

    # Automatic provider resolution: Gemini first, then Claude on any failure.
    errors = []
    if google_key and google_key not in ["your-google-api-key", "your-gemini-api-key"]:
        try:
            return _generate_gemini_suggestion(prompt, google_key, suggestion_type, account_name)
        except AIProviderError as exc:
            errors.append(str(exc))

    if anthropic_key and anthropic_key != "your-anthropic-api-key":
        try:
            return _generate_claude_suggestion(prompt, anthropic_key, suggestion_type, account_name)
        except AIProviderError as exc:
            errors.append(str(exc))

    if errors:
        raise AIProviderError("All configured AI providers failed. " + " | ".join(errors))
    raise AIProviderError("No valid AI provider API key is configured.")


def _stub_suggestion(suggestion_type: str, account_name: str = "") -> dict:
    stubs = {
        "title": {
            "titles": [
                f"How I Grew {account_name or 'My Channel'} to 100K in 90 Days",
                "The ONLY Content Strategy You Need in 2026",
                "Stop Making These 7 Creator Mistakes (Watch This Instead)",
                "I Tested Every Viral Trend — Here's What Actually Works",
                "The Algorithm Decoded: Your Complete 2026 Growth Playbook",
            ],
            "reasoning": "Titles use curiosity gaps, social proof, and specific numbers for maximum CTR.",
            "seo_tips": "Include your primary keyword in the first 40 characters for YouTube SEO.",
        },
        "caption": {
            "captions": [
                {"length": "short", "text": "Growth doesn't happen overnight. But with the right strategy, it accelerates. 🚀", "character_count": 80},
                {"length": "medium", "text": "After analyzing 1,000+ viral videos, I found the common pattern. It's not luck — it's a system. Here's what separates the top 1% of creators from everyone else 👇", "character_count": 168},
                {"length": "long", "text": "I spent 6 months studying every viral video in my niche and found something surprising: the best-performing content all shared 3 key elements...\n\n1. A strong hook that creates instant curiosity\n2. A clear promise delivered in the first 30 seconds\n3. A surprising twist or reveal\n\nSave this for your next post and watch your engagement soar! What's your biggest content challenge? Comment below 💬", "character_count": 412},
            ],
        },
        "hook": {
            "hooks": [
                "I'm about to share something that will completely change how you approach content creation...",
                "Nobody talks about this, but it's the #1 reason most creators plateau at 10K subscribers.",
                "In the next 60 seconds, I'll show you the exact framework I used to 10x my reach.",
                "What if I told you the algorithm doesn't care about your production quality?",
                "This single change doubled my views overnight — and it took me 2 minutes to implement.",
            ],
            "hook_types": ["curiosity", "problem", "promise", "challenge", "result"],
            "reasoning": "Each hook creates curiosity, promises value, and uses pattern interrupts.",
        },
        "hashtag": {
            "hashtags": ["#contentcreator", "#socialmediagrowth", "#viralcontent", "#youtubegrowth",
                         "#creatoreconomy", "#contentmarketing", "#digitalmarketing", "#videomarketing",
                         "#growyourchannel", "#socialmediatips", "#contentideas", "#videoediting",
                         "#youtuber", "#instagramgrowth", "#tiktokmarketing", "#personalbranding",
                         "#smallbusiness", "#entrepreneur", "#onlinemarketing", "#contentcreation"],
            "categories": {
                "trending": ["#contentcreator", "#viralcontent", "#creatoreconomy"],
                "niche": ["#youtubegrowth", "#growyourchannel", "#videomarketing"],
                "branded": ["#socialmediagrowth", "#contentmarketing"],
            },
            "avoid": ["#follow4follow", "#like4like", "#spammy", "#irrelevant", "#banned"],
        },
        "posting_time": {
            "recommendations": [
                {"day": "Tuesday", "time": "18:00", "timezone": "EST", "reason": "Highest audience activity based on engagement patterns", "expected_boost": "+25% reach"},
                {"day": "Thursday", "time": "19:30", "timezone": "EST", "reason": "Second peak — midweek viewership surge", "expected_boost": "+18% reach"},
                {"day": "Saturday", "time": "10:00", "timezone": "EST", "reason": "Weekend morning browsing window with lower competition", "expected_boost": "+15% reach"},
            ],
            "frequency": "3 videos/week for maximum algorithm favor without burnout",
        },
        "thumbnail_concept": {
            "concepts": [
                {
                    "title": "High-Contrast Emotion",
                    "description": "Bright yellow background with bold text overlay. Show a surprised/excited face on the left, text on the right.",
                    "colors": ["#FFDD00", "#FF4136", "#FFFFFF"],
                    "text_overlay": "SHOCKING TRUTH ABOUT...",
                    "emotion": "Surprise/Excitement",
                    "ctr_score": 8.5,
                },
                {
                    "title": "Before/After Split",
                    "description": "Split screen showing transformation. Left side muted/grey, right side vibrant and colorful.",
                    "colors": ["#2ECC71", "#1A1A2E", "#FFFFFF"],
                    "text_overlay": "Before vs After",
                    "emotion": "Transformation/Hope",
                    "ctr_score": 7.8,
                },
                {
                    "title": "Minimalist Authority",
                    "description": "Dark background with one strong visual and a power statement in large white text.",
                    "colors": ["#0E172A", "#4F46E5", "#FFFFFF"],
                    "text_overlay": "THE METHOD THAT WORKS",
                    "emotion": "Trust/Authority",
                    "ctr_score": 7.2,
                },
            ],
        },
        "content_calendar": {
            "weeks": [
                {
                    "week": 1,
                    "theme": "Foundation & Introduction",
                    "posts": [
                        {"day": "Monday", "topic": "Channel intro + value proposition", "format": "Talking head", "duration": "8-12 min", "note": "Establish brand voice"},
                        {"day": "Wednesday", "topic": "Top 5 tools I use daily", "format": "Screen recording", "duration": "10-15 min", "note": "High search volume topic"},
                        {"day": "Friday", "topic": "Community Q&A", "format": "Casual vlog", "duration": "5-8 min", "note": "Builds engagement"},
                    ],
                },
                {
                    "week": 2,
                    "theme": "Education & Value",
                    "posts": [
                        {"day": "Tuesday", "topic": "Deep-dive tutorial on core skill", "format": "Tutorial", "duration": "15-20 min", "note": "Evergreen content"},
                        {"day": "Thursday", "topic": "Common mistakes in niche", "format": "Reaction", "duration": "10-12 min", "note": "High engagement topic"},
                        {"day": "Saturday", "topic": "Behind the scenes", "format": "Vlog", "duration": "6-10 min", "note": "Humanizes brand"},
                    ],
                },
            ],
        },
    }
    return stubs.get(suggestion_type, {"message": "Suggestion generated.", "type": suggestion_type})
