"""In-process Cloudflare bypass using nodriver (a real Chromium-based browser).

This is the sidecar-free alternative to :class:`UnflareRequestHandler`: instead
of POSTing to an external Unflare service, it drives a real browser (Google
Chrome recommended) through the Cloudflare challenge to obtain ``cf_clearance``
+ the user-agent, then relies on :class:`CachedCredentialHandler` to cache and
replay them over plain HTTP.

Requires the ``nodriver`` optional extra and a Chromium-based browser (Google
Chrome is the tested choice)::

    pip install pro_sports_transactions[nodriver]

On a headless host, run the process under a virtual display (e.g. ``xvfb-run``);
Cloudflare's managed challenge is not reliably solved by headless Chrome. See
``docs/nodriver/README.md``. The pieces this handler is assembled from live in
:mod:`pro_sports_transactions.nodriver`.
"""

import asyncio
import logging
from typing import Dict, Optional

from ..concurrency.loop_bound_lock import LoopBoundLock
from ..nodriver.browser_session import BrowserSession
from ..nodriver.nodriver_config import NodriverConfig
from ..nodriver.nodriver_credential_source import NodriverCredentialSource
from .base_handler import CachedCredentialHandler

logger = logging.getLogger(__name__)


class NodriverRequestHandler(CachedCredentialHandler):
    """Get credentials from Chrome via nodriver, then cache + replay them.

    Like :class:`UnflareRequestHandler`, the browser is purely a credential
    source: the page it loads is never returned. Every result comes from
    replaying the credentials over plain HTTP, so the first and every later
    response are the same raw server HTML, and a Cloudflare block page (which
    lacks the challenge marker and may sit beside a leftover ``cf_clearance``
    in the reused browser) never reaches the parser - the replay gets a 403.

    Attributes:
        config: The handler configuration.
        session: Owns the browser process (launch, reuse, event-loop changes).
        source: Drives Chrome through the challenge and returns credentials.
        solve_lock: Serializes browser solves so concurrent cold-start
            requests trigger one solve, not one each.
    """

    def __init__(self, config: Optional[NodriverConfig] = None):
        super().__init__()
        self.config = config or NodriverConfig()
        self.session = BrowserSession(self.config)
        self.source = NodriverCredentialSource(self.session, self.config)
        self.solve_lock = LoopBoundLock()

    async def _refresh_cache_and_request(
        self, url: str, headers: Dict[str, str]
    ) -> Optional[str]:
        """Get fresh credentials from Chrome, cache them, and replay ``url``.

        Browser/CDP failures are contained so the handler keeps the
        None-on-failure contract shared with UnflareRequestHandler.
        """
        # Credentials the caller's fast path (get()) already replayed and saw
        # fail; replaying them again under the lock would only repeat that
        # failure (up to a full timeout) before the solve.
        tried = self._cached_cookies if self.is_cache_valid() else None
        async with self.solve_lock.get():
            # A concurrent caller may have solved while we waited for the lock;
            # replay the now-valid cache instead of solving a second time.
            if self.is_cache_valid() and self._cached_cookies != tried:
                cached = await self._try_cached_request(url, headers)
                if cached is not None:
                    return cached

            try:
                credentials = await asyncio.wait_for(
                    self.source.get_credentials(url), self.config.solve_timeout
                )
            except Exception as e:  # browser/CDP failures must not escape get()
                if isinstance(e, asyncio.TimeoutError):
                    logger.warning(
                        "nodriver solve timed out after %ss for %s",
                        self.config.solve_timeout,
                        url,
                    )
                else:
                    logger.warning("nodriver solve failed for %s: %s", url, e)
                # Drop the browser so the next call relaunches it, rather than
                # reusing a wedged instance (live process, dead CDP connection).
                await self.session.close()
                return None
            if credentials is None:
                return None

            self.cache_credentials(
                credentials.cookies, {"User-Agent": credentials.user_agent}
            )
            return await self._try_cached_request(url, headers)

    async def close(self):
        """Stop the underlying browser and free its resources."""
        await self.session.close()
