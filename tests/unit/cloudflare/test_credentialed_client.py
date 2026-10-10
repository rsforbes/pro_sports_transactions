"""Unit tests for CredentialedClient."""

import asyncio
import logging
from unittest.mock import patch

import aiohttp
import pytest

from pro_sports_transactions.cloudflare import CredentialedClient, ReplayResult

URL = "http://example.com"
UA = {"User-Agent": "Chrome/154"}


async def fetch(client, session, request_headers=None, cookies="cf_clearance=abc"):
    with patch("aiohttp.ClientSession", return_value=session) as mock_cls:
        with patch("asyncio.sleep"):  # no real backoff between retries
            result = await client.fetch(URL, request_headers or {}, UA, cookies)
    return result, mock_cls


class TestMergeHeaders:
    @pytest.mark.unit
    def test_credential_headers_override_request_headers_case_insensitively(self):
        """A lowercase request "user-agent" must not survive beside the
        credentials' "User-Agent": aiohttp would send both, and Cloudflare
        rejects a UA that does not match the one cf_clearance was issued to."""
        sent = CredentialedClient.merge_headers(
            {"user-agent": "Edge/112", "accept-encoding": "gzip", "referer": "r"},
            {"User-Agent": "Chrome/154"},
            "cf_clearance=abc",
        )

        assert [k for k in sent if k.lower() == "user-agent"] == ["User-Agent"]
        assert sent["User-Agent"] == "Chrome/154"
        assert [k for k in sent if k.lower() == "accept-encoding"] == [
            "Accept-Encoding"
        ]
        assert sent["Accept-Encoding"] == "gzip, deflate, br"
        assert sent["Cookie"] == "cf_clearance=abc"
        assert sent["referer"] == "r"

    @pytest.mark.unit
    def test_fixed_headers_override_credential_headers_case_insensitively(self):
        """Lowercase "accept-encoding"/"cookie" in the credentials (e.g. from
        Unflare) must not be sent beside the fixed ones."""
        sent = CredentialedClient.merge_headers(
            {"User-Agent": "Edge/112"},
            {"user-agent": "Chrome/154", "accept-encoding": "gzip", "cookie": "x=1"},
            "cf_clearance=abc",
        )

        assert [k for k in sent if k.lower() == "user-agent"] == ["user-agent"]
        assert sent["user-agent"] == "Chrome/154"
        assert [k for k in sent if k.lower() == "cookie"] == ["Cookie"]
        assert sent["Cookie"] == "cf_clearance=abc"

    @pytest.mark.unit
    def test_no_cookie_header_without_cookies(self):
        sent = CredentialedClient.merge_headers({}, UA, None)

        assert "Cookie" not in sent


class TestIsRejection:
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "status, headers, body, rejected",
        [
            (403, {}, "Forbidden", True),
            (503, {"cf-mitigated": "challenge"}, "", True),
            (503, {"cf-mitigated": "Challenge"}, "", True),
            (503, {}, "<script>window._cf_chl_opt={}</script>", True),
            (503, {}, "Service Unavailable", False),
            (404, {}, "Not Found", False),
        ],
    )
    def test_classifies_failed_responses(self, status, headers, body, rejected):
        assert CredentialedClient.is_rejection(status, headers, body) is rejected


class TestFetch:
    @pytest.mark.unit
    def test_at_least_one_attempt_is_required(self):
        with pytest.raises(ValueError, match="attempts"):
            CredentialedClient(attempts=0)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_success_returns_the_page(self, response, session):
        result, mock_cls = await fetch(
            CredentialedClient(), session(get=response(text="<html>OK</html>"))
        )

        assert result == ReplayResult(text="<html>OK</html>")
        kwargs = mock_cls.call_args.kwargs
        assert kwargs["headers"]["Cookie"] == "cf_clearance=abc"
        assert kwargs["headers"]["User-Agent"] == "Chrome/154"
        assert isinstance(kwargs["timeout"], aiohttp.ClientTimeout)
        assert kwargs["timeout"].total == 120

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rejection_is_reported(self, response, session, caplog):
        with caplog.at_level(logging.WARNING):
            result, _ = await fetch(
                CredentialedClient(), session(get=response(403, text="Forbidden"))
            )

        assert result == ReplayResult(rejected=True)
        assert "Session credentials rejected (403)" in caplog.text

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_site_failure_is_not_a_rejection(self, response, session, caplog):
        with caplog.at_level(logging.WARNING):
            result, _ = await fetch(
                CredentialedClient(),
                session(get=response(500, text="Internal Server Error")),
            )

        assert result == ReplayResult()
        assert "Cached-session request failed with status 500" in caplog.text

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_transient_errors_are_retried(self, response, session):
        client = CredentialedClient()
        flaky = session(get=aiohttp.ClientConnectionError("reset"))
        ok = session(get=response(text="<html>OK</html>"))

        with patch("aiohttp.ClientSession", side_effect=[flaky, flaky, ok]):
            with patch("asyncio.sleep"):
                result = await client.fetch(URL, {}, UA, None)

        assert result.text == "<html>OK</html>"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_persistent_transient_errors_fail_after_the_attempts(self, session):
        client = CredentialedClient(attempts=3)
        broken = session(get=aiohttp.ClientConnectionError("reset"))

        result, mock_cls = await fetch(client, broken)

        assert result == ReplayResult()
        assert mock_cls.call_count == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_timeout_is_not_retried(self, session):
        result, mock_cls = await fetch(
            CredentialedClient(), session(get=asyncio.TimeoutError())
        )

        assert result == ReplayResult()
        assert mock_cls.call_count == 1
