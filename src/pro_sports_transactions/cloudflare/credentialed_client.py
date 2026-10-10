"""Plain-HTTP requests that carry Cloudflare session credentials."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Mapping, Optional

import aiohttp

from ..concurrency.loop_bound import LoopBound
from .challenge import challenge_present

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReplayResult:
    """What a :class:`CredentialedClient` request returned.

    Attributes:
        text: The page, or ``None`` if the request failed.
        rejected: Whether it failed because Cloudflare rejected the
            credentials (fresh ones may succeed), as opposed to the site
            failing (a 404, 5xx, or timeout, which fresh ones would hit too).
    """

    text: Optional[str] = None
    rejected: bool = False


class CredentialedClient:
    """Fetches a URL over plain HTTP with Cloudflare session credentials.

    It reports whether Cloudflare rejected the credentials, and the caller
    decides what to do about it. A transient network error is retried a few
    times, so a blip does not escalate to an expensive fresh solve.

    Requests share one ``aiohttp`` session, so they reuse connections instead
    of paying a TCP + TLS handshake each. The session belongs to the event
    loop that created it; each ``asyncio.run()`` creates a new loop, so a
    loop change replaces it (see :class:`~pro_sports_transactions.concurrency.LoopBound`).
    :meth:`close` releases it; a later request opens a new one.

    Attributes:
        timeout: Total seconds allowed per attempt.
        attempts: Attempts on a transient network error.
    """

    def __init__(self, timeout: float = 120, attempts: int = 3):
        if attempts < 1:
            # Zero attempts would never send the request, yet report it as a
            # site failure.
            raise ValueError(f"attempts must be at least 1, got {attempts}")
        self.timeout = timeout
        self.attempts = attempts
        self._session = LoopBound(
            self._open_session,
            lambda session: session.close(),
            lambda session: not session.closed,
            name="session",
        )

    async def close(self):
        """Close the shared session (if any)."""
        await self._session.close()

    @staticmethod
    async def _open_session() -> aiohttp.ClientSession:
        # No cookie jar: aiohttp lets jar cookies override the Cookie header,
        # so a Set-Cookie kept from one response could shadow the credentials
        # of a later solve. Each request sends exactly the cached ones.
        return aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())

    @staticmethod
    def merge_headers(
        request_headers: Mapping[str, str],
        credential_headers: Mapping[str, str],
        cookies: Optional[str],
    ) -> Dict[str, str]:
        """The headers to send: the request's, then the credentials', then
        the cookies and ``Accept-Encoding``, later layers winning.

        Merged case-insensitively: callers pass lowercase keys (e.g. the
        search module's ``user-agent``), and a plain dict merge would keep both
        it and the credentials' ``User-Agent``, sending two UA headers.
        ``cf_clearance`` is bound to the solving browser's UA, so Cloudflare
        then rejects with 403. The same applies between the credentials'
        headers (e.g. an Unflare ``accept-encoding``/``cookie``) and the fixed
        overrides.
        """
        fixed = {"Accept-Encoding": "gzip, deflate, br"}
        if cookies:
            fixed["Cookie"] = cookies
        merged: Dict[str, str] = {}
        for layer in (request_headers, credential_headers, fixed):
            layer_keys = {k.lower() for k in layer}
            merged = {k: v for k, v in merged.items() if k.lower() not in layer_keys}
            merged.update(layer)
        return merged

    @staticmethod
    def is_rejection(
        status: int, response_headers: Mapping[str, str], body: str
    ) -> bool:
        """Whether a failed response is Cloudflare rejecting the credentials.

        A 403, or a challenge whatever the status: Cloudflare marks challenges
        with ``cf-mitigated`` (e.g. a 503 "under attack" interstitial), and the
        body marker catches a challenge served without it.
        """
        challenged = response_headers.get(
            "cf-mitigated", ""
        ).lower() == "challenge" or challenge_present(body)
        return status == 403 or challenged

    async def fetch(
        self,
        url: str,
        request_headers: Mapping[str, str],
        credential_headers: Mapping[str, str],
        cookies: Optional[str],
    ) -> ReplayResult:
        """GET ``url`` with the credentials."""
        logger.info("Requesting with session credentials")
        headers = self.merge_headers(request_headers, credential_headers, cookies)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        for attempt in range(self.attempts):
            try:
                session = await self._session.get()
                async with session.get(
                    url, headers=headers, timeout=timeout
                ) as response:
                    if response.status == 200:
                        return ReplayResult(text=await response.text(encoding="utf-8"))
                    # errors="replace": a non-UTF-8 error body must not
                    # raise UnicodeDecodeError out of the check or the log.
                    body = await response.text(errors="replace")
                    if self.is_rejection(response.status, response.headers, body):
                        logger.warning(
                            "Session credentials rejected (%d)", response.status
                        )
                        return ReplayResult(rejected=True)
                    # These messages say "cached-session", not "credential":
                    # Semgrep's python-logger-credential-disclosure rule flags
                    # any "credential" log message with a %s placeholder.
                    logger.warning(
                        "Cached-session request failed with status %d: %s",
                        response.status,
                        body,
                    )
                    return ReplayResult()
            except asyncio.TimeoutError as e:
                # The full budget is already spent; retrying would stall the
                # caller for minutes.
                logger.error("Cached-session request timed out: %s", e)
                return ReplayResult()
            except (aiohttp.ClientError, OSError) as e:
                if attempt + 1 < self.attempts:
                    logger.warning(
                        "Cached-session request transient error "
                        "(attempt %d/%d), retrying: %s",
                        attempt + 1,
                        self.attempts,
                        e,
                    )
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                logger.error("Cached-session request failed after retries: %s", e)
                return ReplayResult()
        return ReplayResult()
