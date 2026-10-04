"""Direct HTTP request handler implementation."""

from typing import Dict, Optional

import aiohttp

from .base_handler import RequestHandler


class DirectRequestHandler(RequestHandler):
    """Direct HTTP request handler - no proxy or special handling"""

    async def get(self, url: str, headers: Dict[str, str]) -> Optional[str]:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                return (
                    None
                    if response.status != 200
                    else await response.text(encoding="utf-8")
                )

    async def close(self):
        """Release resources held by the handler. Nothing to release: each request
        opens and closes its own session.

        Every built-in handler supports ``close()`` and ``async with``, so
        handlers can be swapped without changing the calling code. (Defined on
        the concrete handlers rather than the abstract ``RequestHandler`` so
        custom handlers' method resolution is unaffected.)
        """

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()
