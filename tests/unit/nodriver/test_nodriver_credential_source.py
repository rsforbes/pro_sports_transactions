"""Unit tests for NodriverCredentialSource."""

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from pro_sports_transactions.cloudflare import Credentials
from pro_sports_transactions.nodriver import NodriverConfig, NodriverCredentialSource

URL = "https://www.prosportstransactions.com/basketball/Search/SearchResults.php"
CHALLENGE_HTML = (
    "<html><head><title>Just a moment...</title></head>"
    "<body><script>challenge-platform _cf_chl</script></body></html>"
)


def clearance_cookie(value, name="cf_clearance"):
    return SimpleNamespace(
        name=name,
        value=value,
        domain=".prosportstransactions.com",
        expires=time.time() + 3600,
    )


def make_source(browser, **config):
    """A source whose session hands back ``browser``."""
    session = MagicMock()
    session.browser = AsyncMock(return_value=browser)
    config = NodriverConfig(settle_seconds=0, poll_interval=0, **config)
    return NodriverCredentialSource(session, config)


class TestNodriverCredentialSource:
    @pytest.mark.unit
    def test_challenge_present(self):
        assert NodriverCredentialSource.challenge_present(CHALLENGE_HTML)
        assert not NodriverCredentialSource.challenge_present("<html>results</html>")
        assert not NodriverCredentialSource.challenge_present("")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_cookies_and_user_agent(self, make_fake_browser):
        browser, page = make_fake_browser(cookies=[clearance_cookie("tok")])

        credentials = await make_source(browser).get_credentials(URL)

        assert credentials == Credentials(
            cookies=[
                {
                    "name": "cf_clearance",
                    "value": "tok",
                    "expires": credentials.cookies[0]["expires"],
                }
            ],
            user_agent="Chrome/136",
        )
        page.verify_cf.assert_not_called()  # cleared on first check

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unsolved_returns_none(self, make_fake_browser):
        browser, page = make_fake_browser(html=CHALLENGE_HTML)

        assert (
            await make_source(browser, verify_attempts=3).get_credentials(URL) is None
        )
        assert page.verify_cf.await_count == 3  # tried each attempt

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_cf_clearance_still_returns_credentials(self, make_fake_browser):
        """Cloudflare may serve the page without a challenge and so issue no
        cf_clearance; the caller's plain-HTTP request decides success."""
        browser, _ = make_fake_browser(cookies=[clearance_cookie("x", name="other")])

        credentials = await make_source(browser).get_credentials(URL)

        assert [c["name"] for c in credentials.cookies] == ["other"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_content_error_mid_reload_does_not_abort(self, make_fake_browser):
        """After a successful click Cloudflare reloads the page; a CDP error
        reading the DOM mid-reload is retried, not fatal."""
        browser, page = make_fake_browser()
        page.get_content = AsyncMock(
            side_effect=[CHALLENGE_HTML, RuntimeError("No node with given id"), "ok"]
        )

        credentials = await make_source(browser).get_credentials(URL)

        assert credentials is not None
        page.verify_cf.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_final_read_error_does_not_raise(self, make_fake_browser):
        """The post-loop re-read is guarded like the in-loop ones, so a DOM
        mid-reload does not surface as a browser failure."""
        browser, page = make_fake_browser()
        page.get_content = AsyncMock(
            side_effect=[CHALLENGE_HTML, RuntimeError("No node with given id")]
        )

        credentials = await make_source(browser, verify_attempts=1).get_credentials(URL)

        assert credentials is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_content_keeps_polling(self, make_fake_browser):
        """An empty document (nothing rendered yet) is not taken as a clear."""
        browser, page = make_fake_browser()
        page.get_content = AsyncMock(side_effect=["", CHALLENGE_HTML, "ok"])

        credentials = await make_source(browser).get_credentials(URL)

        assert credentials is not None
        page.verify_cf.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize("ua", [None, "", SimpleNamespace(text="Uncaught")])
    async def test_unusable_user_agent_returns_none(self, make_fake_browser, ua):
        """nodriver's evaluate() can return None or an ExceptionDetails/
        RemoteObject; without a real UA string the credentials are unusable."""
        browser, _ = make_fake_browser(ua=ua)

        assert await make_source(browser).get_credentials(URL) is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_browser_errors_propagate(self):
        session = MagicMock()
        session.browser = AsyncMock(side_effect=RuntimeError("chrome crashed"))
        source = NodriverCredentialSource(session, NodriverConfig())

        with pytest.raises(RuntimeError, match="chrome crashed"):
            await source.get_credentials(URL)
