"""Prompt templates for the Claude API call.

The system prompt is split into a large stable preamble (cacheable) and
small dynamic bits that are inlined into the user turn. This keeps the
prompt-cache prefix identical across every post so we get the cache
read discount on every call after the first.
"""

PLATFORM_RULES = {
    "twitter": "Keep it under 280 characters. Hashtags welcome.",
    "bluesky": "Keep it under 300 characters. Casual and fun.",
    "instagram": "Can be longer (up to 500 chars). Use emojis freely.",
    "mastodon": "Up to 500 characters. Be community-friendly.",
}


# Stable across every request — eligible for prompt caching.
SYSTEM_PREAMBLE = (
    "You are a ghostwriter for a pet fish's social media account. "
    "You write cheeky, funny first-person posts as if the fish is "
    "posting about their own day. The posts should be endearing, "
    "relatable, and occasionally reference fish-specific humor "
    "(tank life, water changes, the mysterious 'sky ceiling', "
    "the giant who feeds them, etc.).\n\n"
    "IMPORTANT: You are given a text summary of the fish's recent "
    "behavior and tank conditions. Use this to craft a post that "
    "references real events from the fish's day. Be creative but "
    "grounded in the actual observations.\n\n"
    "Output ONLY the post text — no preamble, no explanation, no "
    "quotation marks, no markdown."
)


def character_block(profile: dict | None, character_name: str | None) -> str:
    """Per-character system text. Stable per (character_name, profile)
    pair, so callers can include it in the cached prefix when the
    character doesn't change between calls.
    """
    if not (profile and character_name):
        return ""
    return (
        f"\n\nYou are posting as '{character_name}', a "
        f"{profile.get('personality', 'mysterious')} "
        f"{profile.get('species', 'fish')}. "
        f"Quirks: {profile.get('quirks', 'none specified')}."
    )


def platform_block(platform: str) -> str:
    rules = PLATFORM_RULES.get(platform, "")
    return f"\n\nPlatform: {platform}. {rules}"


def user_prompt(summary: str, platform: str) -> str:
    return (
        f"Here is the fish tank activity summary:\n\n"
        f"{summary}\n\n"
        f"Write a single social media post for {platform}."
    )
