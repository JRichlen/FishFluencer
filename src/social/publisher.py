"""Platform API adapters for social media publishing."""

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class PlatformPublisher(Protocol):
    """Protocol for platform-specific publishers."""

    def publish(self, content: str) -> dict:
        """Publish content and return result metadata."""
        ...


class TwitterPublisher:
    """Placeholder for Twitter/X API integration."""

    def __init__(self, credentials: dict):
        self.credentials = credentials

    def publish(self, content: str) -> dict:
        logger.info("Twitter publish: %s...", content[:80])
        raise NotImplementedError("Twitter API integration pending")


class BlueskyPublisher:
    """Placeholder for Bluesky API integration."""

    def __init__(self, credentials: dict):
        self.credentials = credentials

    def publish(self, content: str) -> dict:
        logger.info("Bluesky publish: %s...", content[:80])
        raise NotImplementedError("Bluesky API integration pending")


class PublisherFactory:
    """Create platform-specific publishers from config."""

    _registry = {
        "twitter": TwitterPublisher,
        "bluesky": BlueskyPublisher,
    }

    @classmethod
    def create(cls, platform: str, credentials: dict) -> PlatformPublisher:
        if platform not in cls._registry:
            raise ValueError(f"Unsupported platform: {platform}")
        return cls._registry[platform](credentials)
