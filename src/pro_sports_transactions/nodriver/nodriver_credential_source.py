"""Obtains Cloudflare session credentials by driving Chrome through the challenge."""

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

from ..cloudflare.challenge import CHALLENGE_MARKER, challenge_present

# Re-exported: CHALLENGE_MARKER was defined here before moving to cloudflare/.
__all__ = ["CHALLENGE_MARKER", "NodriverCredentialSource"]
from ..cloudflare.credentials import Credentials
from .browser_session import BrowserSession
from .cookie_harvester import CookieHarvester

if TYPE_CHECKING:  # avoid a runtime import cycle through handlers/
    from .nodriver_config import NodriverConfig

logger = logging.getLogger(__name__)


class NodriverCredentialSource:
    """Loads a URL in the browser, clears the Cloudflare challenge, and returns the
    resulting cookies + user-agent.

    The page Chrome loads is deliberately not returned: callers fetch the real
    content over plain HTTP with these credentials. Whether the credentials
    actually work is decided by that request, not here.
    """

    def __init__(
        self,
        session: BrowserSession,
        config: "NodriverConfig",
        cookie_harvester: Optional[CookieHarvester] = None,
    ):
        self.session = session
        self.config = config
        self.cookie_harvester = cookie_harvester or CookieHarvester()

    @staticmethod
    def challenge_present(html: str) -> bool:
        """True while the HTML is still a Cloudflare challenge interstitial."""
        return challenge_present(html)

    async def get_credentials(self, url: str) -> Optional[Credentials]:
        """Credentials for ``url``'s host, or ``None`` if the challenge could
        not be cleared or the user-agent could not be read.

        Browser/CDP errors propagate; the caller decides how to contain them.
        """
        browser = await self.session.browser()
        page = await browser.get(url)
        await asyncio.sleep(self.config.settle_seconds)

        html = ""
        for _ in range(self.config.verify_attempts):
            try:
                html = await page.get_content()
            except Exception as e:  # DOM gone mid-reload right after a solve
                logger.debug("get_content failed (page navigating?): %s", e)
                html = ""
                await asyncio.sleep(self.config.poll_interval)
                continue
            if not html:  # nothing rendered yet; not evidence of a clear
                await asyncio.sleep(self.config.poll_interval)
                continue
            if not self.challenge_present(html):
                break
            try:
                await page.verify_cf()
            except Exception as e:  # nodriver raises broadly on CV misses
                logger.debug("verify_cf attempt failed: %s", e)
            await asyncio.sleep(self.config.poll_interval)
        else:
            # Re-read once more: the final verify_cf above is never followed by a
            # content check inside the loop, so a last-attempt clear would be missed.
            # Guarded like the in-loop read: a DOM mid-reload is not a browser
            # failure, and letting it raise would make the caller discard the
            # (healthy) browser. The plain-HTTP replay then decides success.
            try:
                html = await page.get_content()
            except Exception as e:
                logger.debug("final get_content failed (page navigating?): %s", e)
                html = ""

        if self.challenge_present(html):
            logger.warning("nodriver could not clear the challenge for %s", url)
            return None

        # cf_clearance is not required: Cloudflare may serve the page without a
        # challenge (lower security level, good IP reputation) and so issue no
        # clearance cookie. The caller's plain-HTTP request decides success.
        cookies = await self.cookie_harvester.harvest(browser, url)

        user_agent = await page.evaluate("navigator.userAgent")
        # nodriver's evaluate() returns an ExceptionDetails/RemoteObject (truthy,
        # not a str) on a failed or unserialised evaluation; caching that as a
        # header would make every later request raise inside aiohttp.
        if not isinstance(user_agent, str) or not user_agent:
            logger.warning("could not read the browser user-agent for %s", url)
            return None

        return Credentials(cookies=cookies, user_agent=user_agent)
