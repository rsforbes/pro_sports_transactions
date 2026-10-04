"""Shared fixtures for unit tests."""

import sys
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def fake_nodriver():
    """Stand in for the optional nodriver package. It is imported when a
    BrowserSession is constructed, and CI installs without the [nodriver] extra."""
    module = MagicMock()
    with patch.dict(sys.modules, {"nodriver": module}):
        yield module


@pytest.fixture
def make_fake_browser():
    """Factory for a mock nodriver browser whose page clears on first check."""

    def make(
        html="<html><table><tr><td>data</td></tr></table></html>",
        ua="Chrome/136",
        cookies=None,
    ):
        page = MagicMock()
        page.get_content = AsyncMock(return_value=html)

        async def _evaluate(expr):
            return ua if "userAgent" in expr else None

        page.evaluate = AsyncMock(side_effect=_evaluate)
        page.verify_cf = AsyncMock()

        browser = MagicMock()
        browser.stopped = False
        browser.get = AsyncMock(return_value=page)
        browser.cookies = MagicMock()
        browser.cookies.get_all = AsyncMock(
            return_value=[
                SimpleNamespace(
                    name="cf_clearance",
                    value="token",
                    domain=".prosportstransactions.com",
                    expires=time.time() + 3600,
                )
            ]
            if cookies is None
            else cookies
        )
        browser.stop = MagicMock()
        return browser, page

    return make
