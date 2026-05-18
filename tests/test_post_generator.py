"""Post generator — verifies prompt assembly without hitting the real API."""

from src.social.templates import (
    SYSTEM_PREAMBLE,
    character_block,
    platform_block,
    user_prompt,
)


def test_system_preamble_is_stable():
    """The preamble must not contain timestamps or UUIDs that would
    silently invalidate the prompt cache."""
    assert "{" not in SYSTEM_PREAMBLE  # no format strings
    assert "2026" not in SYSTEM_PREAMBLE  # no embedded date
    assert "{{" not in SYSTEM_PREAMBLE  # no template placeholders


def test_character_block_with_profile():
    block = character_block(
        {"personality": "dramatic", "species": "betta", "quirks": "flares a lot"},
        "Sir Bubbles",
    )
    assert "Sir Bubbles" in block
    assert "dramatic" in block
    assert "betta" in block
    assert "flares a lot" in block


def test_character_block_without_profile_is_empty():
    assert character_block(None, None) == ""
    assert character_block({"personality": "shy"}, None) == ""
    assert character_block(None, "Sir Bubbles") == ""


def test_platform_block_known_platform():
    block = platform_block("twitter")
    assert "twitter" in block
    assert "280 characters" in block


def test_platform_block_unknown_platform_is_safe():
    # No crash, just empty rules
    assert "unknown-platform" in platform_block("unknown-platform")


def test_user_prompt_includes_summary():
    prompt = user_prompt("Sir Bubbles is glass surfing", "twitter")
    assert "Sir Bubbles is glass surfing" in prompt
    assert "twitter" in prompt
