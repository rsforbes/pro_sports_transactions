"""Shared fixtures for the integration and performance tests."""

import socket
from urllib.parse import urlsplit

import pytest

from pro_sports_transactions.handlers import UnflareConfig


@pytest.fixture(scope="session")
def unflare_config():
    """An UnflareConfig for the local Unflare service (the config's default URL).

    Skips only when nothing is listening there. A service that is reachable but
    can't solve a page is not skipped: the tests' own assertions fail on it,
    which is the regression they exist to catch. The probe doesn't solve a page
    itself, so the first Unflare request a test times is still a cold one.
    """
    config = UnflareConfig()
    url = urlsplit(config.url)
    try:
        socket.create_connection((url.hostname, url.port), timeout=5).close()
    except OSError as e:  # refused, unresolvable, or timed out
        pytest.skip(f"Unflare service not reachable at {config.url}: {e}")
    return config
