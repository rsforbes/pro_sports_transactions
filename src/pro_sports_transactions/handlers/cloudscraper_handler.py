"""Cloudscraper request handler for bypassing Cloudflare protection."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Optional

import cloudscraper

from .base_handler import RequestConfig, RequestHandler

logger = logging.getLogger(__name__)


@dataclass
class CloudscraperConfig(RequestConfig):
    """Configuration for Cloudscraper requests."""

    browser: str = "chrome"
    delay: int = 5
    interpreter: str = "native"
    captcha: Optional[Dict] = None


class CloudscraperRequestHandler(  # pylint: disable=too-few-public-methods
    RequestHandler
):
    """Cloudscraper request handler for bypassing Cloudflare protection.

    Uses the cloudscraper library to solve Cloudflare challenges locally
    without requiring external services. Since cloudscraper is synchronous
    (requests-based), calls are wrapped with asyncio.to_thread().
    """

    def __init__(self, config: Optional[CloudscraperConfig] = None):
        self.config = config or CloudscraperConfig()
        scraper_kwargs = {
            "browser": {"browser": self.config.browser},
            "delay": self.config.delay,
            "interpreter": self.config.interpreter,
        }
        if self.config.captcha:
            scraper_kwargs["captcha"] = self.config.captcha
        self._scraper = cloudscraper.create_scraper(**scraper_kwargs)

    async def get(self, url: str, headers: Dict[str, str]) -> Optional[str]:
        logger.info("Requesting %s via cloudscraper", url)
        try:
            response = await asyncio.to_thread(self._scraper.get, url, headers=headers)
            if response.status_code != 200:
                logger.warning(
                    "Cloudscraper request returned status %d for %s",
                    response.status_code,
                    url,
                )
                return None
            return response.text
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Cloudscraper request failed for %s: %s", url, e)
            return None
