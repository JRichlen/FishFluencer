"""
Claude API integration for generating social media posts.

PRIVACY: Only text is sent to the API. Never image data, file paths,
base64, or any binary content. The summarizer module converts visual
observations into text descriptions on-device first.
"""

import logging

import anthropic

from src.social.templates import (
    SYSTEM_PREAMBLE,
    character_block,
    platform_block,
    user_prompt,
)

logger = logging.getLogger(__name__)


class PostGenerator:
    def __init__(
        self,
        api_key: str,
        fish_profiles: dict,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 512,
    ):
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is empty. Set it via systemd "
                "Environment= directive (see docs/hardware/bringup.md)."
            )
        self.model = model
        self.max_tokens = max_tokens
        self.fish_profiles = fish_profiles
        self._client = anthropic.Anthropic(api_key=api_key, timeout=30.0)

    def generate_post(
        self,
        summary: str,
        platform: str = "twitter",
        character_name: str | None = None,
    ) -> str:
        """Generate a social media post from a text-only behavior summary.

        Args:
            summary: Text summary from BehaviorSummarizer (no images).
            platform: Target platform for length/style calibration.
            character_name: Which fish character should "write" the post.
        """
        profile = (
            self.fish_profiles.get(character_name)
            if character_name else None
        )

        # Split the system prompt into a stable cacheable prefix and a
        # volatile suffix. The preamble + character context don't change
        # between scheduled posts, so they get the cache read discount.
        stable_prefix = SYSTEM_PREAMBLE + character_block(profile, character_name)
        volatile_suffix = platform_block(platform)

        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=[
                {
                    "type": "text",
                    "text": stable_prefix,
                    "cache_control": {"type": "ephemeral"},
                },
                {"type": "text", "text": volatile_suffix},
            ],
            messages=[
                {"role": "user", "content": user_prompt(summary, platform)},
            ],
        )

        post_text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

        usage = response.usage
        logger.info(
            "Generated %s post (%d chars). Tokens: in=%d out=%d "
            "cache_read=%d cache_write=%d",
            platform,
            len(post_text),
            usage.input_tokens,
            usage.output_tokens,
            getattr(usage, "cache_read_input_tokens", 0) or 0,
            getattr(usage, "cache_creation_input_tokens", 0) or 0,
        )
        return post_text
