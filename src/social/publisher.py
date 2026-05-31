"""Platform publisher adapters.

Each platform is an adapter that accepts a post string and either
publishes it or no-ops with a warning. The default `DryRunPublisher`
just logs — wire up real credentials by adding a new adapter and
registering it in `make_publisher()`.
"""

import logging
import os
from typing import Protocol

logger = logging.getLogger(__name__)


class Publisher(Protocol):
    def publish(self, platform: str, content: str) -> str: ...


class DryRunPublisher:
    """Logs the post but does not actually publish.

    This is the default — wiring up real platform credentials is a
    deliberate, per-deployment step. Live posting requires the user to
    register the relevant adapter explicitly.
    """

    def publish(self, platform: str, content: str) -> str:
        logger.info("[DRY RUN] [%s] %s", platform, content)
        return "dry_run"


class TwitterPublisher:
    """Twitter/X publisher.

    Requires the env vars: TWITTER_BEARER_TOKEN (OAuth2 user context
    bearer). Uses the v2 POST /2/tweets endpoint.
    """

    def __init__(self):
        self.token = os.environ.get("TWITTER_BEARER_TOKEN")
        if not self.token:
            raise RuntimeError(
                "TWITTER_BEARER_TOKEN not set. Either set it via "
                "systemd Environment=, or fall back to DryRunPublisher."
            )

    def publish(self, platform: str, content: str) -> str:
        import httpx

        response = httpx.post(
            "https://api.twitter.com/2/tweets",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            json={"text": content},
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()
        tweet_id = data.get("data", {}).get("id", "")
        logger.info("Published to twitter: id=%s", tweet_id)
        return tweet_id


class BlueskyPublisher:
    """Bluesky publisher.

    Requires env vars: BLUESKY_HANDLE, BLUESKY_APP_PASSWORD.
    Uses the AT Protocol XRPC endpoint.
    """

    def __init__(self):
        self.handle = os.environ.get("BLUESKY_HANDLE")
        self.password = os.environ.get("BLUESKY_APP_PASSWORD")
        if not (self.handle and self.password):
            raise RuntimeError(
                "BLUESKY_HANDLE / BLUESKY_APP_PASSWORD not set."
            )

    def publish(self, platform: str, content: str) -> str:
        import datetime
        import httpx

        with httpx.Client(timeout=15.0) as client:
            session = client.post(
                "https://bsky.social/xrpc/com.atproto.server.createSession",
                json={"identifier": self.handle, "password": self.password},
            )
            session.raise_for_status()
            jwt = session.json()["accessJwt"]
            did = session.json()["did"]

            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            post = client.post(
                "https://bsky.social/xrpc/com.atproto.repo.createRecord",
                headers={"Authorization": f"Bearer {jwt}"},
                json={
                    "repo": did,
                    "collection": "app.bsky.feed.post",
                    "record": {
                        "text": content,
                        "createdAt": now,
                        "$type": "app.bsky.feed.post",
                    },
                },
            )
            post.raise_for_status()
            uri = post.json().get("uri", "")
            logger.info("Published to bluesky: %s", uri)
            return uri


_REGISTRY = {
    "twitter": TwitterPublisher,
    "bluesky": BlueskyPublisher,
}


def make_publisher(platform: str) -> Publisher:
    """Pick a publisher for the given platform.

    Returns DryRunPublisher if the platform's required env vars are
    missing, so a misconfigured device still logs posts instead of
    crashing the orchestrator.
    """
    cls = _REGISTRY.get(platform)
    if cls is None:
        logger.warning("Unknown platform %s — using DryRunPublisher", platform)
        return DryRunPublisher()
    try:
        return cls()
    except RuntimeError as e:
        logger.warning(
            "Cannot init %s publisher (%s) — falling back to dry run", platform, e
        )
        return DryRunPublisher()
