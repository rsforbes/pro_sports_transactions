"""Direct HTTP request handler implementation."""
from typing import Dict, Optional

import aiohttp

from .base_handler import RequestHandler


class DirectRequestHandler(RequestHandler):  # pylint: disable=too-few-public-methods
    """Direct HTTP request handler - no proxy or special handling"""

    async def get(self, url: str, headers: Dict[str, str]) -> Optional[str]:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                return (
                    None
                    if response.status != 200
                    else await response.text(encoding="utf-8")
                )
