"""Recognising a Cloudflare challenge interstitial."""

# Marker that identifies a Cloudflare challenge interstitial. It must be
# challenge-ONLY: the "challenge-platform" beacon script is injected into normal
# protected pages too (unusable here), and the English "just a moment" title can
# legitimately appear in real page content (false positives). The "_cf_chl"
# challenge object (window._cf_chl_opt/_ctx) is set only on the interstitial and
# is locale-independent.
CHALLENGE_MARKER = "_cf_chl"


def challenge_present(html: str) -> bool:
    """True while the HTML is a Cloudflare challenge interstitial."""
    # The marker is a lowercase JS identifier, so no case-folding (which would
    # copy the whole page on every poll) is needed.
    return bool(html) and CHALLENGE_MARKER in html
