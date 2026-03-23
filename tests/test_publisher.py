"""Tests for src/social/publisher.py"""

import pytest

from social.publisher import BlueskyPublisher, PublisherFactory, TwitterPublisher


class TestTwitterPublisher:
    def test_publish_not_implemented(self):
        pub = TwitterPublisher(credentials={"key": "val"})
        with pytest.raises(NotImplementedError):
            pub.publish("Hello")


class TestBlueskyPublisher:
    def test_publish_not_implemented(self):
        pub = BlueskyPublisher(credentials={"key": "val"})
        with pytest.raises(NotImplementedError):
            pub.publish("Hello")


class TestPublisherFactory:
    def test_create_twitter(self):
        pub = PublisherFactory.create("twitter", {"key": "val"})
        assert isinstance(pub, TwitterPublisher)

    def test_create_bluesky(self):
        pub = PublisherFactory.create("bluesky", {"key": "val"})
        assert isinstance(pub, BlueskyPublisher)

    def test_create_unsupported(self):
        with pytest.raises(ValueError, match="Unsupported platform"):
            PublisherFactory.create("tiktok", {})
