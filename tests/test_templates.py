"""Tests for src/social/templates.py"""

from social.templates import ERROR_ANALYSIS_TEMPLATE, SOCIAL_POST_TEMPLATE


class TestTemplates:
    def test_social_post_template_has_placeholders(self):
        assert "{summary}" in SOCIAL_POST_TEMPLATE
        assert "{platform}" in SOCIAL_POST_TEMPLATE

    def test_social_post_template_format(self):
        result = SOCIAL_POST_TEMPLATE.format(summary="Fish is resting", platform="twitter")
        assert "Fish is resting" in result
        assert "twitter" in result

    def test_error_analysis_template_has_placeholder(self):
        assert "{report}" in ERROR_ANALYSIS_TEMPLATE

    def test_error_analysis_template_format(self):
        result = ERROR_ANALYSIS_TEMPLATE.format(report="NullPointerError in detector.py")
        assert "NullPointerError" in result
