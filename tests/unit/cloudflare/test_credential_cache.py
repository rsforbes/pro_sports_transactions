"""Unit tests for CredentialCache."""

import time

import pytest

from pro_sports_transactions.cloudflare import CredentialCache


def clearance(expires_in=1000):
    return {"name": "cf_clearance", "value": "abc", "expires": time.time() + expires_in}


class TestCredentialCache:
    @pytest.mark.unit
    def test_starts_empty(self):
        cache = CredentialCache()

        assert not cache.is_valid()
        assert cache.cookies is None
        assert cache.headers is None
        assert cache.expiry == 0

    @pytest.mark.unit
    def test_store_builds_the_cookie_header(self):
        cache = CredentialCache()

        cache.store(
            [{"name": "cf_clearance", "value": "abc"}, {"name": "x", "value": "1"}],
            {"User-Agent": "UA"},
        )

        assert cache.cookies == "cf_clearance=abc; x=1"
        assert cache.headers == {"User-Agent": "UA"}
        assert cache.is_valid()

    @pytest.mark.unit
    def test_store_copies_the_headers(self):
        """cf_clearance is bound to the user-agent it was issued with: a caller
        changing its dict afterwards must not change what is sent."""
        cache = CredentialCache()
        headers = {"User-Agent": "UA"}

        cache.store([], headers)
        headers["User-Agent"] = "Other"

        assert cache.headers == {"User-Agent": "UA"}

    @pytest.mark.unit
    def test_each_store_is_a_new_generation(self):
        cache = CredentialCache()

        first = cache.store([], {"User-Agent": "UA"})
        second = cache.store([], {"User-Agent": "UA"})

        assert second == first + 1 == cache.generation

    @pytest.mark.unit
    def test_cookieless_credentials_are_valid(self):
        """A solve that cleared without a challenge may yield no cookies; that
        is still a reusable session."""
        cache = CredentialCache()
        cache.store([], {"User-Agent": "UA"})

        assert cache.is_valid()
        assert cache.cookies is None

    @pytest.mark.unit
    def test_expiry_follows_cf_clearance_minus_the_refresh_margin(self):
        """cf_clearance gates access: a short-lived companion (__cf_bm) must not
        cap the cache, and a long-lived first-party cookie must not extend it."""
        cache = CredentialCache()
        now = time.time()
        cache.store(
            [
                {"name": "__cf_bm", "value": "b", "expires": now + 60},
                {"name": "cf_clearance", "value": "c", "expires": now + 3600},
                {"name": "site", "value": "s", "expires": now + 86400},
            ],
            {},
        )

        assert cache.expiry == pytest.approx(now + 3600 - 300)

    @pytest.mark.unit
    def test_expiry_falls_back_to_the_earliest_cookie_then_an_hour(self):
        cache = CredentialCache()
        now = time.time()

        cache.store([{"name": "a", "value": "1", "expires": now + 900}], {})
        assert cache.expiry == pytest.approx(now + 900 - 300)

        cache.store([{"name": "a", "value": "1"}], {})
        assert cache.expiry == pytest.approx(now + 3600 - 300, abs=5)

    @pytest.mark.unit
    def test_null_expires_falls_back_to_the_default_lifetime(self):
        """A JSON null ``expires`` must not raise TypeError."""
        cache = CredentialCache()
        cache.store([{"name": "cf_clearance", "value": "abc", "expires": None}], {})

        assert cache.is_valid()

    @pytest.mark.unit
    def test_a_malformed_store_leaves_the_cache_unchanged(self):
        """New headers must never be paired with the previous expiry."""
        cache = CredentialCache()
        cache.store([clearance()], {"User-Agent": "UA"})
        before = (cache.cookies, cache.headers, cache.expiry, cache.generation)

        with pytest.raises(TypeError):
            cache.store(
                [{"name": "cf_clearance", "value": "new", "expires": "soon"}],
                {"User-Agent": "Other"},
            )

        assert (cache.cookies, cache.headers, cache.expiry, cache.generation) == before

    @pytest.mark.unit
    def test_credentials_within_the_refresh_margin_are_not_valid(self):
        cache = CredentialCache()
        cache.store([clearance(expires_in=200)], {"User-Agent": "UA"})

        assert not cache.is_valid()

    @pytest.mark.unit
    def test_holds_ignores_expiry_but_not_replacement_or_clearing(self):
        cache = CredentialCache()
        generation = cache.store([clearance(expires_in=200)], {"User-Agent": "UA"})

        assert cache.holds(generation)  # expired, but still the ones cached
        cache.store([clearance()], {"User-Agent": "UA"})
        assert not cache.holds(generation)
        assert cache.holds(cache.generation)
        cache.clear()
        assert not cache.holds(cache.generation)

    @pytest.mark.unit
    def test_clear(self):
        cache = CredentialCache()
        cache.store([clearance()], {"User-Agent": "UA"})

        cache.clear()

        assert not cache.is_valid()
        assert cache.cookies is None
        assert cache.expiry == 0
