"""Reads the cookies for one host from a nodriver browser."""

from typing import List
from urllib.parse import urlparse


class CookieHarvester:
    """Extracts the cookies that apply to a URL's host from a nodriver browser.

    Reads nodriver's cookie store (``browser.cookies.get_all()``), whose items are
    Chrome DevTools Protocol cookie objects with ``name``/``value``/``domain``/
    ``expires`` attributes. Other browser tools (Playwright, Selenium) return
    cookies in different shapes. Not to be confused with nodriver's own
    ``CookieJar`` class, which is what ``browser.cookies`` is.
    """

    @staticmethod
    def host_matches(host: str, domain: str) -> bool:
        """True if a cookie ``domain`` applies to ``host`` (exact or suffix),
        avoiding the false positives of a plain substring test."""
        host = host.lower()
        domain = domain.lower().lstrip(".")
        return bool(domain) and (host == domain or host.endswith("." + domain))

    async def harvest(self, browser, url: str) -> List[dict]:
        """Cookies for ``url``'s host, as ``{"name", "value"[, "expires"]}``
        dicts (the format ``CachedCredentialHandler.cache_credentials`` takes).
        """
        host = (urlparse(url).hostname or "").lower()
        harvested: List[dict] = []
        for c in await browser.cookies.get_all():
            name = getattr(c, "name", None)
            value = getattr(c, "value", None)
            if not name or value is None:
                continue
            domain = getattr(c, "domain", "") or ""
            # Keep host-only cookies (empty domain); for domain cookies require a
            # real host/suffix match.
            if domain and not self.host_matches(host, domain):
                continue
            cookie = {"name": name, "value": value}
            expires = getattr(c, "expires", None)
            if expires and expires > 0:
                cookie["expires"] = expires
            harvested.append(cookie)
        return harvested
