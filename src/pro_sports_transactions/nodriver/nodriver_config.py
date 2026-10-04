"""Configuration for the nodriver in-process Cloudflare bypass."""

from dataclasses import dataclass, field
from typing import List, Optional

from ..handlers.base_handler import RequestConfig


@dataclass
class NodriverConfig(RequestConfig):
    """Configuration for :class:`NodriverRequestHandler`.

    Attributes:
        browser_executable_path: Path to a Chromium-based browser binary.
            ``None`` lets nodriver auto-detect Chrome/Chromium. Google Chrome is
            the only browser verified to clear the challenge; Playwright's
            bundled Chromium failed in testing; Edge/Brave are untested.
        headless: Run Chrome headless. Defaults to ``False`` because the managed
            challenge is not reliably solved headless; use a virtual display
            (xvfb) on headless hosts instead.
        sandbox: Enable Chrome's sandbox. Defaults to ``False`` for containers.
        verify_attempts: Max Turnstile solve attempts before giving up.
        poll_interval: Seconds between solve attempts.
        settle_seconds: Seconds to wait after navigation before the first check.
        solve_timeout: Upper bound in seconds on one whole browser solve
            (navigation, polling, cookie/user-agent reads). A wedged browser
            otherwise hangs ``get()`` - and every caller queued behind the
            solve lock - indefinitely.
        browser_args: Extra Chrome command-line args.
    """

    browser_executable_path: Optional[str] = None
    headless: bool = False
    sandbox: bool = False
    verify_attempts: int = 8
    poll_interval: float = 3.0
    settle_seconds: float = 2.0
    solve_timeout: float = 120.0
    browser_args: List[str] = field(default_factory=lambda: ["--disable-dev-shm-usage"])
