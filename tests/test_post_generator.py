"""Tests for src/social/post_generator.py"""

from unittest.mock import MagicMock, patch

from social.post_generator import PLATFORM_RULES, PostGenerator


class TestPostGenerator:
    def test_init(self):
        gen = PostGenerator(api_key="test-key", fish_profiles={})
        assert gen.api_key == "test-key"
        assert gen.model == "claude-sonnet-4-20250514"
        assert gen.max_tokens == 300

    def test_build_system_prompt_no_character(self):
        gen = PostGenerator(api_key="test", fish_profiles={})
        prompt = gen._build_system_prompt("twitter")
        assert "ghostwriter" in prompt
        assert "twitter" in prompt.lower()

    def test_build_system_prompt_with_character(self):
        profiles = {"Jordan": {"personality": "chill", "species": "fish", "quirks": "loves food"}}
        gen = PostGenerator(api_key="test", fish_profiles=profiles)
        prompt = gen._build_system_prompt("twitter", "Jordan")
        assert "Jordan" in prompt
        assert "chill" in prompt
        assert "loves food" in prompt

    def test_build_system_prompt_unknown_character(self):
        gen = PostGenerator(api_key="test", fish_profiles={})
        prompt = gen._build_system_prompt("twitter", "Unknown")
        # Should not crash, just no character context
        assert "ghostwriter" in prompt

    def test_platform_rules(self):
        assert "280" in PLATFORM_RULES["twitter"]
        assert "300" in PLATFORM_RULES["bluesky"]
        assert "500" in PLATFORM_RULES["instagram"]
        assert "500" in PLATFORM_RULES["mastodon"]

    @patch("social.post_generator.httpx.Client")
    def test_generate_post(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Just vibing in my tank 🐟"}]
        }
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        gen = PostGenerator(api_key="test-key", fish_profiles={})
        gen._client = mock_client

        result = gen.generate_post("Fish is cruising", platform="twitter")
        assert result == "Just vibing in my tank 🐟"
        mock_client.post.assert_called_once()

    @patch("social.post_generator.httpx.Client")
    def test_generate_post_empty_response(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": []}
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        gen = PostGenerator(api_key="test-key", fish_profiles={})
        gen._client = mock_client

        result = gen.generate_post("Summary text")
        assert result == ""
