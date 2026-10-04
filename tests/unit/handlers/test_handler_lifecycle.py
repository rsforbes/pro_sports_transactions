"""All built-in handlers share one calling pattern, so they can be swapped by
changing a single constructor."""

import pytest

from pro_sports_transactions.handlers import (
    DirectRequestHandler,
    NodriverRequestHandler,
    UnflareConfig,
    UnflareRequestHandler,
)

HANDLERS = [DirectRequestHandler, UnflareRequestHandler, NodriverRequestHandler]

pytestmark = pytest.mark.usefixtures("fake_nodriver")


class TestHandlerLifecycle:
    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize("handler_cls", HANDLERS, ids=lambda c: c.__name__)
    async def test_constructs_without_arguments_and_supports_async_with(
        self, handler_cls
    ):
        async with handler_cls() as handler:
            assert isinstance(handler, handler_cls)

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize("handler_cls", HANDLERS, ids=lambda c: c.__name__)
    async def test_close_is_safe_to_call_repeatedly(self, handler_cls):
        handler = handler_cls()
        await handler.close()
        await handler.close()

    @pytest.mark.unit
    def test_unflare_defaults_to_default_config(self):
        assert UnflareRequestHandler().config == UnflareConfig()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_keeps_cached_credentials(self):
        """Closing releases resources, not the cached Cloudflare session."""
        handler = UnflareRequestHandler()
        handler.cache_credentials([{"name": "cf_clearance", "value": "abc"}], {})
        await handler.close()
        assert handler.has_cached_cookies
