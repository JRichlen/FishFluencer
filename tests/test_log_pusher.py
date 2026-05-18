"""Verify the error-report redaction strips common secret shapes."""

from src.sync.log_pusher import _redact


def test_redacts_anthropic_key():
    msg = "Auth failed with key sk-ant-api03-abcdefghij1234567890"
    out = _redact(msg)
    assert "sk-ant" not in out
    assert "[REDACTED]" in out


def test_redacts_github_pat():
    out = _redact("token = ghp_abcdefghij1234567890")
    assert "ghp_" not in out
    assert "[REDACTED]" in out


def test_redacts_bearer_token():
    out = _redact("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxxxxxxx.yyyyyyyyyy")
    assert "eyJ" not in out


def test_redacts_password_kwarg():
    out = _redact("connect(host='x', password='hunter2')")
    assert "hunter2" not in out


def test_redacts_user_home_path():
    out = _redact("FileNotFoundError: /home/mendel/secrets/key.pem")
    assert "/home/mendel" not in out


def test_passes_through_safe_text():
    out = _redact("Failed to read /sys/bus/w1/devices/28-foo/w1_slave")
    assert out == "Failed to read /sys/bus/w1/devices/28-foo/w1_slave"
