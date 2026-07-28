"""
Social Pulse API — Claude AI Client
Builds prompts from video patterns and calls Anthropic Claude API.
"""
import json
from flask import current_app

SUGGESTION_TYPE_INSTRUCTIONS = {
    "title": (
        "Generate 5 compelling YouTube/social media video title ideas "
        "that are highly clickable, SEO-optimized, and match the content patterns below. "
        "Return JSON: {\"titles\": [\"Title 1\", ..., \"Title 5\"], \"reasoning\": \"...\"}"
    ),
    "caption": (
        "Write 3 engaging social media captions (short, medium, long variants) "
        "that would work well for the content pattern below. "
        "Return JSON: {\"captions\": [{\"length\": \"short\", \"text\": \"...\"}, ...]}"
    ),
    "hook": (
        "Generate 5 powerful video hook lines (first 5-10 seconds) "
        "that instantly capture viewer attention based on these patterns. "
        "Return JSON: {\"hooks\": [\"Hook 1\", ..., \"Hook 5\"], \"reasoning\": \"...\"}"
    ),
    "hashtag": (
        "Suggest 20 highly relevant hashtags (mix of popular and niche) "
        "based on the content patterns below. "
        "Return JSON: {\"hashtags\": [\"#tag1\", ...], \"categories\": {\"broad\": [...], \"niche\": [...]}}"
    ),
    "thumbnail_concept": (
        "Describe 3 thumbnail concepts (colors, text overlay, composition, emotions) "
        "that would maximize click-through rate based on these video patterns. "
        "Return JSON: {\"concepts\": [{\"title\": \"...\", \"description\": \"...\", \"colors\": [...]}]}"
    ),
    "posting_time": (
        "Based on these video performance patterns, recommend the top 3 best days/times "
        "to post new content for maximum reach. "
        "Return JSON: {\"recommendations\": [{\"day\": \"Monday\", \"time\": \"18:00\", \"reason\": \"...\"}]}"
    ),
    "content_calendar": (
        "Create a 4-week content calendar with topic ideas, formats, and posting schedule "
        "based on these performance patterns. "
        "Return JSON: {\"weeks\": [{\"week\": 1, \"posts\": [{\"day\": \"Mon\", \"topic\": \"...\", \"format\": \"...\"}]}]}"
    ),
}


def _build_prompt(suggestion_type: str, videos: list, account_name: str = "") -> str:
    """Build a detailed prompt from video patterns for Claude."""
    instruction = SUGGESTION_TYPE_INSTRUCTIONS.get(
        suggestion_type,
        "Generate a content suggestion based on these patterns."
    )

    # Build pattern summary
    top_videos = sorted(videos, key=lambda v: v.get("views", 0), reverse=True)[:10]
    pattern_lines = []
    for i, v in enumerate(top_videos, 1):
        tags = ", ".join((v.get("tags") or [])[:5]) or "none"
        pattern_lines.append(
            f"{i}. \"{v.get('title', 'No title')}\" | "
            f"Views: {v.get('views', 0):,} | "
            f"Likes: {v.get('likes', 0):,} | "
            f"Comments: {v.get('comments', 0):,} | "
            f"Duration: {v.get('duration_seconds', 0)}s | "
            f"Tags: {tags}"
        )

    patterns_text = "\n".join(pattern_lines) if pattern_lines else "No videos available."
    account_line = f"Channel/Account: {account_name}\n" if account_name else ""

    prompt = (
        f"You are an expert social media growth strategist for Social Pulse.\n\n"
        f"{account_line}"
        f"Task: {instruction}\n\n"
        f"Top performing videos/posts (sorted by views):\n{patterns_text}\n\n"
        f"Provide ONLY valid JSON as your response. No markdown, no explanation outside the JSON."
    )
    return prompt


def generate_suggestion(suggestion_type: str, videos: list, account_name: str = "") -> dict:
    """
    Call Claude API to generate a content suggestion.
    Falls back to mock data if ANTHROPIC_API_KEY is not set.
    """
    api_key = current_app.config.get("ANTHROPIC_API_KEY", "")
    prompt = _build_prompt(suggestion_type, videos, account_name)

    if not api_key:
        current_app.logger.warning("ANTHROPIC_API_KEY not set — using stub suggestion.")
        return _stub_suggestion(suggestion_type, account_name)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text.strip()
        # Try to extract JSON
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            # Find JSON in response
            import re
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return {"raw": raw_text}
    except Exception as e:
        current_app.logger.error(f"Claude API error: {e}")
        return _stub_suggestion(suggestion_type, account_name)


def _stub_suggestion(suggestion_type: str, account_name: str = "") -> dict:
    """Return realistic stub data for demo purposes."""
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
        },
        "caption": {
            "captions": [
                {"length": "short", "text": "Growth doesn't happen overnight. But with the right strategy, it accelerates. 🚀"},
                {"length": "medium", "text": "After analyzing 1,000+ viral videos, I found the common pattern. It's not luck — it's a system. Here's what separates the top 1% of creators from everyone else 👇"},
                {"length": "long", "text": "I spent 6 months studying every viral video in my niche and found something surprising: the best-performing content all shared 3 key elements...\n\n1. A strong hook that creates instant curiosity\n2. A clear promise delivered in the first 30 seconds\n3. A surprising twist or reveal\n\nSave this for your next post and watch your engagement soar! What's your biggest content challenge? Comment below 💬"},
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
            "reasoning": "Each hook creates curiosity, promises value, and uses pattern interrupts.",
        },
        "hashtag": {
            "hashtags": ["#contentcreator", "#socialmediagrowth", "#viralcontent", "#youtubegrowth",
                         "#creatoreconomy", "#contentmarketing", "#digitalmarketing", "#videomarketing",
                         "#growyourchannel", "#socialmediatips", "#contentideas", "#videoediting",
                         "#youtuber", "#instagramgrowth", "#tiktokmarketing", "#personalbranding",
                         "#smallbusiness", "#entrepreneur", "#onlinemarketing", "#contentcreation"],
            "categories": {
                "broad": ["#contentcreator", "#socialmediagrowth", "#digitalmarketing", "#entrepreneur"],
                "niche": ["#youtubegrowth", "#growyourchannel", "#creatoreconomy", "#videomarketing"],
            },
        },
        "posting_time": {
            "recommendations": [
                {"day": "Tuesday", "time": "18:00", "timezone": "EST", "reason": "Highest audience activity based on engagement patterns"},
                {"day": "Thursday", "time": "19:30", "timezone": "EST", "reason": "Second peak — midweek viewership surge"},
                {"day": "Saturday", "time": "10:00", "timezone": "EST", "reason": "Weekend morning browsing window with lower competition"},
            ],
        },
        "thumbnail_concept": {
            "concepts": [
                {
                    "title": "High-Contrast Emotion",
                    "description": "Bright yellow background with bold text overlay. Show a surprised/excited face on the left, text on the right. Keep it simple and readable at 100px.",
                    "colors": ["#FFDD00", "#FF4136", "#FFFFFF"],
                },
                {
                    "title": "Before/After Split",
                    "description": "Split screen showing transformation. Left side muted/grey, right side vibrant and colorful. Numbers in the center for social proof.",
                    "colors": ["#2ECC71", "#1A1A2E", "#FFFFFF"],
                },
                {
                    "title": "Minimalist Authority",
                    "description": "Dark background with one strong visual element and a power statement in large white text. Conveys expertise and trust.",
                    "colors": ["#0E172A", "#4F46E5", "#FFFFFF"],
                },
            ],
        },
        "content_calendar": {
            "weeks": [
                {
                    "week": 1,
                    "theme": "Foundation",
                    "posts": [
                        {"day": "Monday", "topic": "My journey & channel introduction video", "format": "Talking head + B-roll", "duration": "8-12 min"},
                        {"day": "Wednesday", "topic": "Top 5 tools I use daily (affiliate opportunity)", "format": "Screen recording + voiceover", "duration": "10-15 min"},
                        {"day": "Friday", "topic": "Community Q&A - answer comments from week 1", "format": "Casual talking head", "duration": "5-8 min"},
                    ],
                },
                {
                    "week": 2,
                    "theme": "Value & Education",
                    "posts": [
                        {"day": "Tuesday", "topic": "In-depth tutorial on your core skill", "format": "Tutorial/walkthrough", "duration": "15-20 min"},
                        {"day": "Thursday", "topic": "Common mistakes in your niche (reaction video)", "format": "Reaction + commentary", "duration": "10-12 min"},
                        {"day": "Saturday", "topic": "Behind the scenes - content creation process", "format": "Vlog style", "duration": "6-10 min"},
                    ],
                },
            ],
        },
    }
    return stubs.get(suggestion_type, {"message": "Suggestion generated successfully.", "type": suggestion_type})
