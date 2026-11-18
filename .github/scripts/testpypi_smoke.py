"""Smoke-test an installed pro_sports_transactions against the README.

Run by .github/workflows/testpypi.yml from a checkout, in a clean venv, with
``-I`` so the checkout's ``src/`` can't shadow the installed package:

    python -I testpypi_smoke.py base       # installed without extras
    python -I testpypi_smoke.py nodriver   # installed with [nodriver]; needs a
                                           # display (xvfb-run) and Chrome

CHROME_PATH, if set, is passed as NodriverConfig.browser_executable_path:
auto-detect prefers the shortest path, so an installed Chromium (which failed
in testing) would win over Chrome. Exits non-zero if any check fails.
"""

import asyncio
import os
import sys
from datetime import date
from pathlib import Path

import pro_sports_transactions as pst
from pro_sports_transactions.handlers import (
    NodriverConfig,
    NodriverRequestHandler,
    RequestHandler,
)

# The README Quick Start's search and the rows it shows.
QUICK_START_ROWS = 12
SOLVE_ATTEMPTS = 3  # Turnstile solves occasionally fail; the README says retry

# A saved search results page (3 rows, 1 page), from the unit tests.
FIXTURE = Path(__file__).resolve().parents[2] / "tests/unit/data/valid_response.html"


class FixtureHandler(RequestHandler):
    """Serves the saved results page, so parsing runs without the network."""

    async def get(self, url, headers):
        return FIXTURE.read_text(encoding="utf-8")


def quick_start_search(handler):
    # As in the README Quick Start.
    return pst.Search(
        league=pst.League.NBA,
        transaction_types=tuple(pst.TransactionType),
        start_date=date.fromisoformat("2022-10-18"),
        end_date=date.fromisoformat("2023-04-09"),
        player="LeBron James",
        team="Lakers",
        starting_row=0,
        request_handler=handler,
    )


def check_installed():
    assert "site-packages" in pst.__file__, f"not the installed package: {pst.__file__}"
    print("package:", pst.__file__)


async def check_base():
    # Parsing imports read_html's parsers (lxml etc.) lazily, so only a parse
    # proves the base dependencies are installed.
    df = await quick_start_search(FixtureHandler()).get_dataframe()
    assert "errors" not in df.attrs, f"parse failed: {df.attrs['errors']}"
    assert len(df) == 3 and df.attrs["pages"] == 1, f"unexpected parse: {df}"
    print("ok: parsed a saved results page (3 rows)")

    # README: a missing [nodriver] extra raises ImportError at construction.
    try:
        NodriverRequestHandler()
    except ImportError as e:
        assert "pro_sports_transactions[nodriver]" in str(e), f"no install hint: {e}"
        print("ok: NodriverRequestHandler() without the extra raises ImportError")
    else:
        sys.exit("NodriverRequestHandler() constructed without the nodriver extra")


async def check_nodriver():
    config = NodriverConfig(browser_executable_path=os.environ.get("CHROME_PATH"))
    # The README's retry pattern: reuse one handler, back off 1s, 2s, ...
    async with NodriverRequestHandler(config) as handler:
        for attempt in range(SOLVE_ATTEMPTS):
            df = await quick_start_search(handler).get_dataframe()
            print(f"attempt {attempt + 1}: rows={len(df)} {df.attrs}")
            if "errors" not in df.attrs:
                break
            if attempt + 1 < SOLVE_ATTEMPTS:
                await asyncio.sleep(2**attempt)
    assert "errors" not in df.attrs, f"quick start failed: {df.attrs['errors']}"
    assert len(df) == QUICK_START_ROWS, f"expected {QUICK_START_ROWS} rows: {df}"
    print(f"ok: README Quick Start returned {QUICK_START_ROWS} rows")


check_installed()
if sys.argv[1:] == ["base"]:
    asyncio.run(check_base())
elif sys.argv[1:] == ["nodriver"]:
    asyncio.run(check_nodriver())
else:
    sys.exit(__doc__)
