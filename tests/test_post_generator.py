"""Post generator — verifies prompt assembly without hitting the real API."""

import pytest

from src.social.templates import (
    SYSTEM_PREAMBLE,
    SYSTEM_PREAMBLE_DOG,
    SYSTEM_PREAMBLE_FISH,
    character_block,
    platform_block,
    system_preamble,
    user_prompt,
)


def test_system_preamble_is_stable():
    """The preamble must not contain timestamps or UUIDs that would
    silently invalidate the prompt cache."""
    for preamble in (SYSTEM_PREAMBLE_FISH, SYSTEM_PREAMBLE_DOG):
        assert "{" not in preamble  # no format strings
        assert "2026" not in preamble  # no embedded date
        assert "{{" not in preamble  # no template placeholders


def test_back_compat_alias():
    """Existing imports of SYSTEM_PREAMBLE keep working — it aliases the
    fish preamble."""
    assert SYSTEM_PREAMBLE is SYSTEM_PREAMBLE_FISH


def test_system_preamble_picks_by_mode():
    assert system_preamble("fish") is SYSTEM_PREAMBLE_FISH
    assert system_preamble("dog") is SYSTEM_PREAMBLE_DOG


def test_system_preamble_rejects_unknown_mode():
    with pytest.raises(ValueError):
        system_preamble("goldfish-but-with-extra-steps")


def test_dog_preamble_mentions_stress():
    """Stress signals must be taken seriously in dog mode — not played
    for laughs."""
    assert "stress" in SYSTEM_PREAMBLE_DOG.lower()
    assert "pacing" in SYSTEM_PREAMBLE_DOG.lower()


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


def test_user_prompt_fish_mode():
    prompt = user_prompt("Sir Bubbles is glass surfing", "twitter", mode="fish")
    assert "Sir Bubbles is glass surfing" in prompt
    assert "twitter" in prompt
    assert "fish tank" in prompt


def test_user_prompt_dog_mode():
    prompt = user_prompt("Rex is pacing", "bluesky", mode="dog")
    assert "Rex is pacing" in prompt
    assert "bluesky" in prompt
    assert "kennel" in prompt
