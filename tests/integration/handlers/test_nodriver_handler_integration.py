"""Integration tests for NodriverRequestHandler (live prosportstransactions.com).

Requires the [nodriver] extra, a real Google Chrome, and a display. In the dev
container there is no display, so run under a virtual one:

    xvfb-run -a python -m pytest tests/integration/handlers/test_nodriver_handler_integration.py
"""

import importlib.util
import os
import shutil
import sys
from datetime import date

import pytest

from pro_sports_transactions.handlers import NodriverConfig, NodriverRequestHandler
from pro_sports_transactions.search import League, Search, TransactionType, headers

URL = (
    "https://www.prosportstransactions.com/basketball/Search/"
    "SearchResults.php?BeginDate=2023-01-01&EndDate=2023-01-31&Submit=Search"
    "&PlayerMovementChkBx=yes"
)

# The results table on a real (non-challenge) search page.
RESULTS_TABLE = '<table class="datatable center">'


def _skip_reason():
    """Why this environment can't drive a live Chrome, or None if it can."""
    if importlib.util.find_spec("nodriver") is None:
        return "nodriver extra not installed (uv sync --all-extras)"
    if sys.platform.startswith("linux"):
        if not _chrome_path():
            return "Google Chrome not installed"
        if not os.environ.get("DISPLAY"):
            return "no display - run under xvfb-run"
    return None


def _chrome_path():
    """The Google Chrome binary the skip check found (None elsewhere, letting
    nodriver auto-detect). Passed explicitly because auto-detect prefers the
    shortest path, so an installed Chromium would win over Chrome and fail."""
    return shutil.which("google-chrome") or shutil.which("google-chrome-stable")


pytestmark = pytest.mark.skipif(_skip_reason() is not None, reason=str(_skip_reason()))


class TestNodriverHandlerIntegration:
    """Live tests: the first request solves in Chrome, later ones replay the cache."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_solve_then_cached_replay(self):
        config = NodriverConfig(browser_executable_path=_chrome_path())
        async with NodriverRequestHandler(config) as handler:
            # First call: browser clears the challenge and caches cf_clearance.
            first = await handler.get(URL, headers)
            assert first is not None, "browser solve failed"
            assert RESULTS_TABLE in first
            assert handler.is_cache_valid()

            # Second call: cached credentials replayed over plain aiohttp.
            second = await handler.get(URL, headers)
            assert second is not None, "cached replay failed"
            assert RESULTS_TABLE in second

            # End to end through the public Search API, reusing the cache.
            df = await Search(
                league=League.NBA,
                transaction_types=(TransactionType.Movement,),
                start_date=date(2023, 1, 1),
                end_date=date(2023, 1, 31),
                request_handler=handler,
            ).get_dataframe()
            assert not df.empty
