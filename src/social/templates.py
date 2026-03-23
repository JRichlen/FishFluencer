"""Prompt templates for Claude post generation."""

SOCIAL_POST_TEMPLATE = """Here is the fish tank activity summary:

{summary}

Write a single social media post for {platform}."""

ERROR_ANALYSIS_TEMPLATE = """An automated error report was filed from a FishFluencer device.
Analyze this error and propose a minimal, targeted fix.

Error report:
{report}

Instructions:
1. Read the traceback and identify the root cause
2. Check the suggested_files for context
3. Propose a fix as a new PR against main
4. Include a clear PR description explaining the fix
5. Do NOT modify config files or secrets
6. Keep changes minimal and focused"""
