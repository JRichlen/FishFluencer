"""Prompt templates for the Claude API call.

The system prompt is split into a large stable preamble (cacheable) and
small dynamic bits that are inlined into the user turn. This keeps the
prompt-cache prefix identical across every post so we get the cache
read discount on every call after the first.

Two preambles are available — `fish` (the default) and `dog`. Picked by
``PostGenerator(mode=...)``. The preambles are written so that swapping
between them does not change the request shape, only the cached prefix
content; you do still pay one cache-write the first time a new mode
runs on a device.
"""

PLATFORM_RULES = {
    "twitter": "Keep it under 280 characters. Hashtags welcome.",
    "bluesky": "Keep it under 300 characters. Casual and fun.",
    "instagram": "Can be longer (up to 500 chars). Use emojis freely.",
    "mastodon": "Up to 500 characters. Be community-friendly.",
}


# --- Fish mode preamble (stable across every fish-mode request) -----

SYSTEM_PREAMBLE_FISH = (
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


# --- Dog mode preamble ---------------------------------------------

SYSTEM_PREAMBLE_DOG = (
    "You are a ghostwriter for a pet dog's social media account. "
    "You write cheeky, funny first-person posts as if the dog is "
    "posting about their own day from inside their kennel or run. "
    "The posts should be warm, relatable, and occasionally reference "
    "dog-specific humor (the great outside, the squirrel, the leash, "
    "the food bowl that fills mysteriously, the human who returns, "
    "and so on).\n\n"
    "IMPORTANT: You are given a text summary of the dog's recent "
    "behavior and kennel conditions. Use this to craft a post that "
    "references real events from the dog's day. Be creative but "
    "grounded in the actual observations.\n\n"
    "If the summary indicates sustained pacing or other stress "
    "signals, do NOT make light of it — note it sincerely in the "
    "dog's voice (e.g. 'feeling restless today, where's my human').\n\n"
    "Output ONLY the post text — no preamble, no explanation, no "
    "quotation marks, no markdown."
)


# --- Backward-compat alias: existing code imports SYSTEM_PREAMBLE ---
SYSTEM_PREAMBLE = SYSTEM_PREAMBLE_FISH


_PREAMBLES = {"fish": SYSTEM_PREAMBLE_FISH, "dog": SYSTEM_PREAMBLE_DOG}


def system_preamble(mode: str = "fish") -> str:
    """Pick the stable, cacheable preamble for the given mode."""
    try:
        return _PREAMBLES[mode]
    except KeyError as e:
        raise ValueError(
            f"Unknown mode {mode!r}. Must be one of {list(_PREAMBLES)}."
        ) from e


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
        f"{profile.get('species', 'animal')}. "
        f"Quirks: {profile.get('quirks', 'none specified')}."
    )


def platform_block(platform: str) -> str:
    rules = PLATFORM_RULES.get(platform, "")
    return f"\n\nPlatform: {platform}. {rules}"


# Friendly source description per mode, used in the user turn.
_USER_SOURCE_NOUN = {"fish": "fish tank", "dog": "kennel"}


def user_prompt(summary: str, platform: str, mode: str = "fish") -> str:
    noun = _USER_SOURCE_NOUN.get(mode, "subject")
    return (
        f"Here is the {noun} activity summary:\n\n"
        f"{summary}\n\n"
        f"Write a single social media post for {platform}."
    )
