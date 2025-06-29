"""
curl_cffi utilities for browser impersonation and version checking
"""

import curl_cffi
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CurlCffiInfo:
    """Utilities for checking curl_cffi capabilities and browser support"""

    # Browser priority order for testing (newest first)
    BROWSER_PRIORITY = [
        "chrome136",
        "chrome133a",
        "chrome131",
        "safari18_4",
        "firefox135",
    ]

    @staticmethod
    def get_version() -> str:
        """Get curl_cffi version"""
        return curl_cffi.__version__

    @staticmethod
    def check_browser_availability(
        browsers: Optional[List[str]] = None, timeout: int = 5
    ) -> Dict[str, bool]:
        """
        Check which browser impersonations are available

        Args:
            browsers: List of browser names to check. If None, uses default priority list.
            timeout: Timeout for test requests in seconds

        Returns:
            Dict mapping browser names to availability (True/False)
        """
        if browsers is None:
            browsers = CurlCffiInfo.BROWSER_PRIORITY

        results = {}
        test_url = "https://httpbin.org/user-agent"

        for browser in browsers:
            try:
                response = curl_cffi.get(test_url, impersonate=browser, timeout=timeout)
                results[browser] = response.status_code == 200
                logger.debug(f"Browser {browser}: available")
            except Exception as e:
                results[browser] = False
                logger.debug(f"Browser {browser}: not available - {e}")

        return results

    @staticmethod
    def get_best_available_browser(timeout: int = 5) -> Optional[str]:
        """
        Get the best available browser impersonation (newest first)

        Args:
            timeout: Timeout for test requests in seconds

        Returns:
            Browser name if available, None if none work
        """
        availability = CurlCffiInfo.check_browser_availability(timeout=timeout)

        for browser in CurlCffiInfo.BROWSER_PRIORITY:
            if availability.get(browser, False):
                logger.info(f"Selected browser: {browser}")
                return browser

        logger.warning("No browser impersonations available")
        return None

    @staticmethod
    def get_browser_info(browser: str) -> Dict[str, str]:
        """
        Get information about a specific browser impersonation

        Args:
            browser: Browser name (e.g., "chrome136")

        Returns:
            Dict with browser information
        """
        browser_info = {
            "chrome136": {
                "name": "Chrome 136",
                "platform": "Windows",
                "description": "Latest Chrome version (as of curl_cffi 0.11.0)",
            },
            "chrome133a": {
                "name": "Chrome 133a",
                "platform": "Windows",
                "description": "Chrome 133 alternative (A/B testing variant)",
            },
            "chrome131": {
                "name": "Chrome 131",
                "platform": "Windows",
                "description": "Chrome 131 stable",
            },
            "safari18_4": {
                "name": "Safari 18.4",
                "platform": "macOS",
                "description": "Latest Safari version",
            },
            "firefox135": {
                "name": "Firefox 135",
                "platform": "Windows",
                "description": "Latest Firefox version",
            },
        }

        return browser_info.get(
            browser,
            {
                "name": browser,
                "platform": "Unknown",
                "description": "Browser impersonation",
            },
        )

    @staticmethod
    def print_system_info() -> None:
        """Print comprehensive curl_cffi system information"""
        print(f"curl_cffi version: {CurlCffiInfo.get_version()}")
        print("\nBrowser availability check:")
        print("-" * 40)

        availability = CurlCffiInfo.check_browser_availability()

        for browser in CurlCffiInfo.BROWSER_PRIORITY:
            status = (
                "✅ Available" if availability.get(browser, False) else "❌ Not available"
            )
            info = CurlCffiInfo.get_browser_info(browser)
            print(f"{browser:12} | {status:13} | {info['name']}")

        best = CurlCffiInfo.get_best_available_browser()
        if best:
            print(f"\nRecommended browser: {best}")
        else:
            print(f"\nWarning: No browsers available!")


def test_curl_cffi_setup():
    """Test function to verify curl_cffi installation and capabilities"""
    try:
        CurlCffiInfo.print_system_info()
        return True
    except Exception as e:
        logger.error(f"curl_cffi test failed: {e}")
        return False


if __name__ == "__main__":
    # Run system info when called directly
    test_curl_cffi_setup()
