# CloudscraperRequestHandler

## Summary

`CloudscraperRequestHandler` uses the [cloudscraper](https://github.com/VeNoMouS/cloudscraper) library to bypass Cloudflare protection locally, without requiring external services like Unflare.

## Current Status: Not viable (as of February 2026)

Cloudflare's protection on prosportstransactions.com blocks cloudscraper with a 403 response. The integration tests confirm this — cloudscraper's challenge-solving has not kept pace with modern Cloudflare.

This branch is preserved so the work can be revisited if cloudscraper receives updates that improve its effectiveness.

## How to re-test

```bash
# Install dependencies
poetry install

# Run integration tests against the live site
pytest tests/integration/handlers/test_cloudscraper_handler_integration.py -v -m integration
```

If both integration tests pass, cloudscraper is working against prosportstransactions.com and this branch can be merged.

## Implementation details

- **Handler**: `cloudscraper_handler.py` — wraps the synchronous cloudscraper library with `asyncio.to_thread()` to fit the async `RequestHandler` interface.
- **Config**: `CloudscraperConfig` — exposes `browser`, `delay`, `interpreter`, and `captcha` settings.
- **Unit tests**: 12 tests in `tests/unit/handlers/test_cloudscraper_handler.py` — all pass (mocked, no network).
- **Integration tests**: 3 tests in `tests/integration/handlers/test_cloudscraper_handler_integration.py` — assert real HTML is returned from prosportstransactions.com. These will fail when cloudscraper cannot bypass Cloudflare.
- **Example**: `examples/cloudscraper_search.py` — mirrors the Unflare example.

## Alternatives

- **UnflareRequestHandler** — uses an external Unflare service to solve Cloudflare challenges. Currently the recommended approach.
- **DirectRequestHandler** — no Cloudflare bypass. Blocked by prosportstransactions.com.
