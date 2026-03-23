"""
Claude API integration for generating social media posts.

CRITICAL PRIVACY RULE: Only TEXT is sent to the API. Never image data,
file paths, base64, or any binary content.
"""

import logging

import httpx

logger = logging.getLogger(__name__)

PLATFORM_RULES = {
    "twitter": "Keep it under 280 characters. Hashtags welcome.",
    "bluesky": "Keep it under 300 characters. Casual and fun.",
    "instagram": "Can be longer (up to 500 chars). Use emojis freely.",
    "mastodon": "Up to 500 characters. Be community-friendly.",
}


class PostGenerator:
    def __init__(
        self,
        api_key: str,
        fish_profiles: dict,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 300,
    ):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.fish_profiles = fish_profiles
        self._client = httpx.Client(timeout=30.0)

    def generate_post(
        self,
        summary: str,
        platform: str = "twitter",
        character_name: str = None,
    ) -> str:
        """Generate a social media post from a text-only behavior summary."""
        system_prompt = self._build_system_prompt(platform, character_name)

        response = self._client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": self.max_tokens,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"Here is the fish tank activity summary:\n\n"
                            f"{summary}\n\n"
                            f"Write a single social media post for {platform}."
                        ),
                    }
                ],
            },
        )

        response.raise_for_status()
        data = response.json()

        post_text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                post_text += block["text"]

        logger.info("Generated %s post: %s...", platform, post_text[:80])
        return post_text.strip()

    def _build_system_prompt(self, platform: str, character_name: str = None) -> str:
        """Build the system prompt for Claude."""
        char_context = ""
        if character_name and character_name in self.fish_profiles:
            profile = self.fish_profiles[character_name]
            char_context = (
                f"You are posting as '{character_name}', a {profile['personality']} "
                f"{profile.get('species', 'fish')}. "
                f"Quirks: {profile.get('quirks', 'none specified')}. "
            )

        return (
            "You are a ghostwriter for a pet fish's social media account. "
            "You write cheeky, funny first-person posts as if the fish is "
            "posting about their own day. The posts should be endearing, "
            "relatable, and occasionally reference fish-specific humor "
            "(tank life, water changes, the mysterious 'sky ceiling', "
            "the giant who feeds them, etc.). "
            f"{char_context}"
            f"\nPlatform: {platform}. {PLATFORM_RULES.get(platform, '')}"
            "\n\nIMPORTANT: You are given a text summary of the fish's recent "
            "behavior and tank conditions. Use this to craft a post that "
            "references real events from the fish's day. Be creative but "
            "grounded in the actual observations."
        )
