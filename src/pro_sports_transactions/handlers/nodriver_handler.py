"""In-process Cloudflare bypass using nodriver (a real Chrome browser).

This is the sidecar-free alternative to :class:`UnflareRequestHandler`: instead
of POSTing to an external Unflare service, it drives a real Google Chrome via
nodriver, clicks the Cloudflare Turnstile challenge, harvests the resulting
``cf_clearance`` cookie + user-agent, and hands them to
:class:`CachedCredentialHandler` for cheap replay.

Requires the ``nodriver`` optional extra and a real Chrome install::

    pip install pro_sports_transactions[nodriver]

On a headless host, run the process under a virtual display (e.g. ``xvfb-run``);
Cloudflare's managed challenge is not reliably solved by headless Chrome. See
``docs/nodriver/README.md``.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse

from .base_handler import CachedCredentialHandler, RequestConfig

logger = logging.getLogger(__name__)

_INSTALL_HINT = (
    "NodriverRequestHandler requires the 'nodriver' extra and a real Chrome "
    "install: pip install pro_sports_transactions[nodriver]"
)


@dataclass
class NodriverConfig(RequestConfig):
    """Configuration for the nodriver in-process browser handler.

    Attributes:
        browser_executable_path: Path to a real Chrome binary. ``None`` lets
            nodriver auto-detect. Chrome is required — unbranded Chromium is
            detected by Cloudflare and will not clear the challenge.
        headless: Run Chrome headless. Defaults to ``False`` because the managed
            challenge is not reliably solved headless; use a virtual display
            (xvfb) on headless hosts instead.
        sandbox: Enable Chrome's sandbox. Defaults to ``False`` for containers.
        verify_attempts: Max Turnstile solve attempts before giving up.
        poll_interval: Seconds between solve attempts.
        settle_seconds: Seconds to wait after navigation before the first check.
        browser_args: Extra Chrome command-line args.
    """

    browser_executable_path: Optional[str] = None
    headless: bool = False
    sandbox: bool = False
    verify_attempts: int = 8
    poll_interval: float = 3.0
    settle_seconds: float = 2.0
    browser_args: List[str] = field(default_factory=lambda: ["--disable-dev-shm-usage"])


class NodriverRequestHandler(CachedCredentialHandler):
    """Solve Cloudflare in-process with nodriver, then cache + replay creds."""

    # Marker that identifies a Cloudflare challenge interstitial. It must be
    # challenge-ONLY: the "challenge-platform" beacon script is injected into
    # normal protected pages too (unusable here), and the English "just a
    # moment" title can legitimately appear in real page content (false
    # positives). The "_cf_chl" challenge object (window._cf_chl_opt/_ctx) is
    # set only on the interstitial and is locale-independent. Success is never
    # inferred from the marker's absence alone - it also requires a captured
    # cf_clearance cookie (see _refresh_cache_and_request), so an error/block
    # page that happens to lack the marker is not mistaken for the real page.
    _CHALLENGE_MARKER = "_cf_chl"

    def __init__(self, config: Optional[NodriverConfig] = None):
        super().__init__()
        self.config = config or NodriverConfig()
        self._browser = None
        self._lock = asyncio.Lock()

    @staticmethod
    def _import_nodriver():
        try:
            import nodriver as uc  # noqa: PLC0415
        except ImportError as e:  # pragma: no cover - exercised via install extra
            raise ImportError(_INSTALL_HINT) from e
        return uc

    async def _ensure_browser(self):
        """Start the browser once and reuse it across requests."""
        if self._browser is not None and getattr(self._browser, "stopped", False):
            self._browser = None
        if self._browser is None:
            uc = self._import_nodriver()
            self._browser = await uc.start(
                browser_executable_path=self.config.browser_executable_path,
                headless=self.config.headless,
                sandbox=self.config.sandbox,
                browser_args=list(self.config.browser_args),
            )
        return self._browser

    @classmethod
    def _challenge_present(cls, html: str) -> bool:
        """True while the HTML is still a Cloudflare challenge interstitial."""
        return bool(html) and cls._CHALLENGE_MARKER in html.lower()

    async def _refresh_cache_and_request(
        self, url: str, headers: Dict[str, str]
    ) -> Optional[str]:
        """Drive Chrome to clear the challenge, cache the resulting session, and
        return the page. Browser/CDP failures are contained so the handler keeps
        the None-on-failure contract shared with UnflareRequestHandler."""
        async with self._lock:
            # A concurrent caller may have solved while we waited for the lock;
            # replay the now-valid cache instead of solving a second time.
            if self.is_cache_valid():
                cached = await self._try_cached_request(url, headers)
                if cached is not None:
                    return cached

            try:
                return await self._solve_and_cache(url, headers)
            except Exception as e:  # browser/CDP failures must not escape get()
                logger.warning("nodriver solve failed for %s: %s", url, e)
                return None

    async def _solve_and_cache(
        self, url: str, headers: Dict[str, str]
    ) -> Optional[str]:
        browser = await self._ensure_browser()
        page = await browser.get(url)
        await asyncio.sleep(self.config.settle_seconds)

        html = ""
        for _ in range(self.config.verify_attempts):
            html = await page.get_content()
            if not self._challenge_present(html):
                break
            try:
                await page.verify_cf()
            except Exception as e:  # nodriver raises broadly on CV misses
                logger.debug("verify_cf attempt failed: %s", e)
            await asyncio.sleep(self.config.poll_interval)
        else:
            # Re-read once more: the final verify_cf above is never followed by a
            # content check inside the loop, so a last-attempt clear would be missed.
            html = await page.get_content()

        # Success requires BOTH the challenge gone AND a real cf_clearance cookie.
        # Absence of the marker alone is not enough: a Cloudflare block page
        # (error 1020) or a Chrome net-error page also lacks it, and must not be
        # handed to the parser as a successful fetch.
        cookies = await self._harvest_cookies(browser, url)
        has_clearance = any(c["name"] == "cf_clearance" for c in cookies)
        if self._challenge_present(html) or not has_clearance:
            logger.warning("nodriver did not obtain cf_clearance for %s", url)
            return None

        user_agent = await page.evaluate("navigator.userAgent")
        if not user_agent:
            # Cannot bind cf_clearance to a UA for replay; return the solved page
            # we already hold rather than discarding a successful fetch.
            logger.warning(
                "could not read the browser user-agent for %s; "
                "returning solved page without caching credentials",
                url,
            )
            return html

        # Replay through the shared cached path so the first response and every
        # subsequent cached response are the same raw server HTML (consistent
        # markup for the parser). Fall back to the browser DOM only if that
        # immediate replay fails.
        self.cache_credentials(cookies, {"User-Agent": user_agent})
        replayed = await self._try_cached_request(url, headers)
        return replayed if replayed is not None else html

    @staticmethod
    def _host_matches(host: str, domain: str) -> bool:
        """True if a cookie ``domain`` applies to ``host`` (exact or suffix),
        avoiding the false positives of a plain substring test."""
        host = host.lower()
        domain = domain.lower().lstrip(".")
        return bool(domain) and (host == domain or host.endswith("." + domain))

    async def _harvest_cookies(self, browser, url: str) -> List[dict]:
        """Extract cookies for the target host in cache_credentials' format."""
        host = (urlparse(url).hostname or "").lower()
        harvested: List[dict] = []
        for c in await browser.cookies.get_all():
            name = getattr(c, "name", None)
            value = getattr(c, "value", None)
            if not name or value is None:
                continue
            domain = (getattr(c, "domain", "") or "").lstrip(".")
            # Keep host-only cookies (empty domain); for domain cookies require a
            # real host/suffix match.
            if domain and not self._host_matches(host, domain):
                continue
            cookie = {"name": name, "value": value}
            expires = getattr(c, "expires", None)
            if expires and expires > 0:
                cookie["expires"] = expires
            harvested.append(cookie)
        return harvested

    async def close(self):
        """Stop the underlying browser and free its resources."""
        if self._browser is not None:
            try:
                self._browser.stop()
            except Exception as e:  # pragma: no cover - best-effort teardown
                logger.debug("browser stop failed: %s", e)
            self._browser = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()
