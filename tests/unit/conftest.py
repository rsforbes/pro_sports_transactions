"""Shared fixtures for unit tests."""

import sys
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def make_response(status=200, text="", json=None, headers=None):
    """A mock aiohttp response. ``json`` may be an exception to raise."""
    response = AsyncMock()
    response.status = status
    response.headers = headers or {}
    response.text = AsyncMock(return_value=text)
    if isinstance(json, Exception):
        response.json = AsyncMock(side_effect=json)
    else:
        response.json = AsyncMock(return_value=json)
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    return response


def make_session(get=None, post=None):
    """A mock aiohttp.ClientSession whose get()/post() return the given
    responses (or raise, if given an exception)."""
    session = AsyncMock()
    for name, response in (("get", get), ("post", post)):
        if isinstance(response, Exception):
            setattr(session, name, MagicMock(side_effect=response))
        else:
            setattr(session, name, MagicMock(return_value=response))
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.fixture
def response():
    """Factory for mock aiohttp responses (see make_response)."""
    return make_response


@pytest.fixture
def session():
    """Factory for mock aiohttp sessions (see make_session)."""
    return make_session


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
