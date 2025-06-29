from datetime import date
from enum import Enum, StrEnum
from pandas import DataFrame, read_html
from typing import Dict, Optional, List
from urllib import parse
import aiohttp
import asyncio
import cloudscraper
import curl_cffi
from curl_cffi import AsyncSession, requests as curl_requests
import json
import pandas as pd
from functools import partial
from .curl_cffi_utils import CurlCffiInfo


class League(StrEnum):
    MLB = "baseball"
    NBA = "basketball"
    NFL = "football"
    NHL = "hockey"
    MLS = "soccer"


class TransactionType(Enum):
    Disciplinary = {"default": "DisciplinaryChkBx"}
    InjuredList = {"default": "ILChkBx", "MLB": "DLChkBx"}
    Injury = {"default": "InjuriesChkBx"}
    LegalIncident = {"default": "LegalChkBx"}
    MinorLeagueToFrom = {"default": "NBADLChkBx", "MLB": "MinorsChkBx"}
    Movement = {"default": "PlayerMovementChkBx"}
    PersonalReason = {"default": "PersonalChkBx"}

    def __getitem__(cls, value):
        if type(value) == League:
            name = value.name
            return cls.value[name] if name in cls.value else cls.value["default"]
        else:
            return cls.value


class Search:
    def __init__(
        self,
        league: League = League.NBA,
        transaction_types: TransactionType = (),
        start_date: date = date.today(),
        end_date: date = date.today(),
        player: str = None,
        team: str = None,
        starting_row: int = 0,
    ):
        self._url = UrlBuilder.build(
            league=league,
            transaction_types=transaction_types,
            start_date=start_date,
            end_date=end_date,
            player=player,
            team=team,
            starting_row=starting_row,
        )

    async def _get_dataframe(self) -> DataFrame:
        # Generic DataFrame to hold results
        response = await Http.get(self._url)

        df = None
        try:
            df_list = read_html(response, header=0, keep_default_na=False)
            df = pd.DataFrame(
                df_list[0],
                columns=["Date", "Team", "Acquired", "Relinquished", "Notes"],
            )
            df.attrs["pages"] = int(df_list[1].columns[2].split(" ")[-1])
        except Exception as e:
            df = pd.DataFrame(
                columns=["Date", "Team", "Acquired", "Relinquished", "Notes"]
            )
            df.attrs["pages"] = 0
            df.attrs["errors"] = (repr(e),)

        return df

    async def get_dict(self):
        df = await self._get_dataframe()

        data = {}
        data["transactions"] = df.to_dict(orient="records")
        data["pages"] = df.attrs["pages"]
        if "errors" in df.attrs:
            data["errors"] = df.attrs["errors"]
        return data

    async def get_json(self):
        return json.dumps(await self.get_dict())

    async def get_url(self):
        return self._url


netloc = "https://www.prosportstransactions.com"
path = "Search/SearchResults.php"

headers = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9",
    "connection": "keep-alive",
    "content-type": "text/html; charset=utf-8 ",
    "referer": "https://www.prosportstransactions.com/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
        AppleWebKit/537.36 (KHTML, like Gecko) \
        Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.48"
    ),
}


class Parameter:
    @staticmethod
    def date_param(key: str, value: date) -> Dict:
        return {key: value.strftime("%Y-%m-%d") if type(value) == date else ""}

    @staticmethod
    def transaction_type(param_name) -> Dict:
        return {param_name: "yes"}

    @staticmethod
    def start_date(start_date: date) -> Dict:
        return Parameter.date_param("BeginDate", start_date)

    @staticmethod
    def end_date(end_date: date) -> Dict:
        return Parameter.date_param("EndDate", end_date)

    @staticmethod
    def player(player_name: str) -> Dict:
        return {} if player_name is None else {"Player": player_name}

    @staticmethod
    def team(team_name: str) -> Dict:
        return {} if team_name is None else {"Team": team_name}

    @staticmethod
    def starting_row(starting_row: int) -> Dict:
        return {"start": str(starting_row)}

    @staticmethod
    def submit():
        return {"Submit": "Search"}


class UrlBuilder:
    @staticmethod
    def build(
        league=League.NBA,
        transaction_types=(),
        start_date: date = date.today(),
        end_date: date = date.today(),
        player=None,
        team=None,
        starting_row=None,
    ):
        params = {}
        params |= Parameter.start_date(start_date)
        params |= Parameter.end_date(end_date)
        params |= Parameter.player(player)
        params |= Parameter.team(team)
        params |= Parameter.starting_row(starting_row)
        params |= Parameter.submit()

        # Add all Transaction Type parameter values
        for transaction_type in transaction_types:
            params |= Parameter.transaction_type(
                TransactionType[transaction_type.name][league]
            )

        return f"{netloc}/{league.value}/{path}?{parse.urlencode(params)}"


class CloudscraperConfig:
    """Configuration for cloudscraper integration"""

    def __init__(
        self,
        browser: str = "chrome",
        browser_platform: Optional[str] = "windows",
        browser_mobile: bool = False,
        browser_desktop: bool = True,
        interpreter: str = "js2py",
        delay: int = 15,
        enable_stealth: bool = True,
        stealth_min_delay: float = 1.0,
        stealth_max_delay: float = 3.0,
        stealth_human_like_delays: bool = True,
        stealth_randomize_headers: bool = False,
        stealth_browser_quirks: bool = True,
        allow_brotli: bool = True,
        debug: bool = True,
        custom_headers: Optional[Dict] = None,
        session_cookies: Optional[Dict] = None,
    ):
        self.browser = browser
        self.browser_platform = browser_platform
        self.browser_mobile = browser_mobile
        self.browser_desktop = browser_desktop
        self.interpreter = interpreter
        self.delay = delay
        self.enable_stealth = enable_stealth
        self.stealth_min_delay = stealth_min_delay
        self.stealth_max_delay = stealth_max_delay
        self.stealth_human_like_delays = stealth_human_like_delays
        self.stealth_randomize_headers = stealth_randomize_headers
        self.stealth_browser_quirks = stealth_browser_quirks
        self.allow_brotli = allow_brotli
        self.debug = debug
        self.custom_headers = custom_headers or self.get_exact_browser_headers()
        self.session_cookies = session_cookies or {}

    @staticmethod
    def get_exact_browser_headers() -> Dict:
        """Return exact headers from successful browser access"""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-full-version": '"138.0.7204.50"',
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-platform-version": '"15.0.0"',
            "sec-ch-ua-mobile": "?0",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "sec-gpc": "1",
            "upgrade-insecure-requests": "1",
            "cache-control": "no-cache",
            "pragma": "no-cache",
        }

    def get_working_cf_clearance_cookie(self) -> str:
        """Return the working cf_clearance cookie from browser analysis"""
        return "yuk1QDs5G23aRROdkuOWRG_bjxbrfQRwJSLxJ3KM5lA-1751119949-1.2.1.1-OgJGCygQmKjn08tEb7ACOy4OMqFWvjcvlZ31og1t3arrGuwt5puxCp.ECMYMuBF68dPq7caZFnYhmKpso0iqqQmBQqWXfLwXiSA6HfR7EbXs5D_U887EcKc7xMpCRHc8VDFdfuy07PA9q7vf5zrkm7xtUVPrNRTs5i4clSsSnlWkP_hOpDgxnWzUxDI9o3Q5rvMtAuzaKbeCOE.7Vv24vy0rPV2q6sBkbLZcVBNNoRLtPkdfdB3vuZ8iSD0jzD5QgiIStW20DUWqfq77A5YNzwnC_i7F9IVGo1fJdwrhIgVQlUnmGk2spvApe35BBmUkGni7._eOjkjbQ9qLXpOm9eRakMo47moey.JjjDmb72OkTSTYWxxFIQMd6pEiFbMO"


class CurlCffiConfig:
    """Configuration for curl_cffi browser impersonation"""

    def __init__(
        self,
        browser: str = "chrome136",
        fallback_browsers: Optional[List[str]] = None,
        timeout: int = 30,
        max_redirects: int = 10,
        verify_ssl: bool = True,
        custom_headers: Optional[Dict] = None,
        session_cookies: Optional[Dict] = None,
        proxies: Optional[Dict] = None,
        debug: bool = True,
        request_delay: float = 2.0,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
    ):
        self.browser = browser
        self.fallback_browsers = fallback_browsers or [
            "chrome133a",
            "chrome131",
            "safari18_4",
        ]
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.verify_ssl = verify_ssl
        self.custom_headers = custom_headers or self.get_chrome136_headers()
        self.session_cookies = session_cookies or {}
        self.proxies = proxies
        self.debug = debug
        self.request_delay = request_delay
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        # Validate browser availability
        self.validated_browser = self.get_best_browser()

    def get_best_browser(self) -> str:
        """Get the best available browser, with fallbacks"""
        browsers_to_try = [self.browser] + self.fallback_browsers

        for browser in browsers_to_try:
            try:
                # Quick test to see if browser is available
                curl_cffi.get(
                    "https://httpbin.org/status/200", impersonate=browser, timeout=5
                )
                if self.debug:
                    print(f"Selected browser: {browser}")
                return browser
            except Exception as e:
                if self.debug:
                    print(f"Browser {browser} not available: {e}")
                continue

        # Last resort - let curl_cffi pick default
        if self.debug:
            print("Warning: No specific browser available, using curl_cffi default")
        return "chrome"  # curl_cffi default

    @staticmethod
    def get_chrome136_headers() -> Dict:
        """Return headers that match Chrome 136 fingerprint"""
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            # Note: User-Agent and sec-ch-ua headers are set by curl_cffi impersonation
        }

    def get_working_cf_clearance_cookie(self) -> str:
        """Return the working cf_clearance cookie from browser analysis"""
        return "yuk1QDs5G23aRROdkuOWRG_bjxbrfQRwJSLxJ3KM5lA-1751119949-1.2.1.1-OgJGCygQmKjn08tEb7ACOy4OMqFWvjcvlZ31og1t3arrGuwt5puxCp.ECMYMuBF68dPq7caZFnYhmKpso0iqqQmBQqWXfLwXiSA6HfR7EbXs5D_U887EcKc7xMpCRHc8VDFdfuy07PA9q7vf5zrkm7xtUVPrNRTs5i4clSsSnlWkP_hOpDgxnWzUxDI9o3Q5rvMtAuzaKbeCOE.7Vv24vy0rPV2q6sBkbLZcVBNNoRLtPkdfdB3vuZ8iSD0jzD5QgiIStW20DUWqfq77A5YNzwnC_i7F9IVGo1fJdwrhIgVQlUnmGk2spvApe35BBmUkGni7._eOjkjbQ9qLXpOm9eRakMo47moey.JjjDmb72OkTSTYWxxFIQMd6pEiFbMO"


class Http:
    """HTTP client with Cloudflare bypass capabilities"""

    # Class-level configuration - public for easy testing
    config: CloudscraperConfig = CloudscraperConfig()
    scraper_instance: Optional[cloudscraper.CloudScraper] = None

    @classmethod
    def configure(cls, config: CloudscraperConfig):
        """Configure cloudscraper settings and return HTTP client instance"""
        cls.config = config
        cls.scraper_instance = None  # Force recreation with new config
        return cls.get_scraper()  # Return configured scraper

    @classmethod
    def get_scraper(cls) -> cloudscraper.CloudScraper:
        """Get or create scraper instance with enhanced configuration"""
        if cls.scraper_instance is None:
            # Build browser config
            browser_config = {
                "browser": cls.config.browser,
                "platform": cls.config.browser_platform,
                "mobile": cls.config.browser_mobile,
                "desktop": cls.config.browser_desktop,
            }
            # Remove None values
            browser_config = {k: v for k, v in browser_config.items() if v is not None}

            # Build stealth options
            stealth_options = {
                "min_delay": cls.config.stealth_min_delay,
                "max_delay": cls.config.stealth_max_delay,
                "human_like_delays": cls.config.stealth_human_like_delays,
                "randomize_headers": cls.config.stealth_randomize_headers,
                "browser_quirks": cls.config.stealth_browser_quirks,
            }

            # Create scraper with enhanced anti-detection features
            cls.scraper_instance = cloudscraper.create_scraper(
                browser=browser_config,
                interpreter=cls.config.interpreter,
                delay=cls.config.delay,
                enable_stealth=cls.config.enable_stealth,
                stealth_options=stealth_options if cls.config.enable_stealth else None,
                allow_brotli=cls.config.allow_brotli,
                debug=cls.config.debug,
                # Enhanced session management
                session_refresh_interval=1800,  # 30 minutes
                auto_refresh_on_403=True,
                max_403_retries=3,
                # Request throttling to prevent detection
                min_request_interval=2.0,  # 2 seconds between requests
                max_concurrent_requests=1,
                # TLS evasion
                rotate_tls_ciphers=True,
            )

            # Apply exact browser headers to match working fingerprint
            if cls.config.custom_headers:
                cls.scraper_instance.headers.update(cls.config.custom_headers)

            # Apply session cookies if available
            if cls.config.session_cookies:
                cls.scraper_instance.cookies.update(cls.config.session_cookies)

            # Patch with our enhanced V3 handler for modern challenges
            try:
                import sys
                import os

                # Calculate the absolute path to temp_cloudscraper
                current_file = os.path.abspath(__file__)
                project_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(current_file))
                )
                temp_cloudscraper_path = os.path.join(project_root, "temp_cloudscraper")

                if cls.config.debug:
                    print(f"Looking for patched handler at: {temp_cloudscraper_path}")
                    print(f"Path exists: {os.path.exists(temp_cloudscraper_path)}")

                if temp_cloudscraper_path not in sys.path:
                    sys.path.insert(0, temp_cloudscraper_path)

                # Import the patched handler using importlib
                import importlib.util

                patched_handler_path = os.path.join(
                    temp_cloudscraper_path, "cloudscraper", "cloudflare_v3_patched.py"
                )

                if cls.config.debug:
                    print(f"Loading patched handler from: {patched_handler_path}")
                    print(f"File exists: {os.path.exists(patched_handler_path)}")

                spec = importlib.util.spec_from_file_location(
                    "cloudflare_v3_patched", patched_handler_path
                )
                patched_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(patched_module)

                CloudflareV3Patched = patched_module.CloudflareV3Patched

                # Replace the V3 handler with our patched version
                cls.scraper_instance.cloudflare_v3 = CloudflareV3Patched(
                    cls.scraper_instance
                )

                if cls.config.debug:
                    print(
                        "✅ Patched V3 handler installed for modern Cloudflare challenges"
                    )

            except Exception as e:
                if cls.config.debug:
                    print(f"❌ Could not load patched V3 handler: {e}")
                    print("Using standard cloudscraper V3 handler")
                    import traceback

                    traceback.print_exc()

        return cls.scraper_instance

    @classmethod
    def configure_with_cookie_session(cls, cf_clearance_cookie: str):
        """Configure with working cf_clearance cookie for session reuse"""
        session_cookies = {"cf_clearance": cf_clearance_cookie}

        config_with_session = CloudscraperConfig(
            session_cookies=session_cookies, debug=True
        )

        cls.configure(config_with_session)

    @staticmethod
    async def get(url):
        """Async wrapper around cloudscraper for backward compatibility"""
        scraper = Http.get_scraper()

        # Run synchronous cloudscraper in async context
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, partial(scraper.get, url))

        if Http.config.debug:
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")

        return response.text if response.status_code == 200 else None

    @staticmethod
    def get_sync(url):
        """Synchronous method for direct cloudscraper access"""
        scraper = Http.get_scraper()
        response = scraper.get(url)

        if Http.config.debug:
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")

        return response.text if response.status_code == 200 else None


class CurlCffiHttp:
    """HTTP client using curl_cffi for TLS fingerprint evasion"""

    # Class-level configuration
    config: CurlCffiConfig = CurlCffiConfig()
    session_instance: Optional[AsyncSession] = None

    @classmethod
    def configure(cls, config: CurlCffiConfig):
        """Configure curl_cffi settings and return HTTP client instance"""
        cls.config = config
        cls.session_instance = None  # Force recreation with new config
        return cls.get_session()

    @classmethod
    async def get_session(cls) -> AsyncSession:
        """Get or create async session with browser impersonation"""
        if cls.session_instance is None:
            session_config = {
                "impersonate": cls.config.validated_browser,
                "timeout": cls.config.timeout,
                "verify": cls.config.verify_ssl,
                "proxies": cls.config.proxies,
            }

            cls.session_instance = AsyncSession(**session_config)

            # Apply custom headers
            if cls.config.custom_headers:
                cls.session_instance.headers.update(cls.config.custom_headers)

            # Apply session cookies
            if cls.config.session_cookies:
                cls.session_instance.cookies.update(cls.config.session_cookies)

            if cls.config.debug:
                print(
                    f"✅ curl_cffi session created with browser: {cls.config.validated_browser}"
                )

        return cls.session_instance

    @classmethod
    async def configure_with_cookie_session(cls, cf_clearance_cookie: str):
        """Configure with working cf_clearance cookie for session reuse"""
        session_cookies = {"cf_clearance": cf_clearance_cookie}

        config_with_session = CurlCffiConfig(
            session_cookies=session_cookies, debug=True
        )

        return cls.configure(config_with_session)

    @staticmethod
    async def get(url: str) -> Optional[str]:
        """Async GET request using curl_cffi.requests with retry logic"""

        for attempt in range(CurlCffiHttp.config.retry_attempts):
            try:
                if CurlCffiHttp.config.debug and attempt > 0:
                    print(f"Retry attempt {attempt + 1} for {url}")

                # Add request delay to avoid rate limiting
                if attempt > 0:
                    await asyncio.sleep(CurlCffiHttp.config.retry_delay)
                else:
                    await asyncio.sleep(CurlCffiHttp.config.request_delay)

                # Use curl_cffi.requests interface - simpler and more effective
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: curl_requests.get(
                        url,
                        impersonate=CurlCffiHttp.config.validated_browser,
                        timeout=CurlCffiHttp.config.timeout,
                        verify=CurlCffiHttp.config.verify_ssl,
                        headers=CurlCffiHttp.config.custom_headers,
                        cookies=CurlCffiHttp.config.session_cookies,
                        proxies=CurlCffiHttp.config.proxies,
                    ),
                )

                if CurlCffiHttp.config.debug:
                    print(f"Response status: {response.status_code}")
                    print(f"Response headers: {dict(response.headers)}")

                    # Check for Cloudflare challenge indicators
                    if "cf-mitigated" in response.headers:
                        print(
                            f"⚠️  Cloudflare challenge detected: {response.headers.get('cf-mitigated')}"
                        )

                    if "Just a moment" in response.text:
                        print("⚠️  Cloudflare waiting page detected")

                if response.status_code == 200:
                    return response.text
                elif response.status_code in [403, 429, 503]:
                    if CurlCffiHttp.config.debug:
                        print(f"❌ Blocked by Cloudflare: {response.status_code}")
                    continue  # Retry
                else:
                    if CurlCffiHttp.config.debug:
                        print(f"⚠️  Unexpected status: {response.status_code}")
                    return None

            except asyncio.TimeoutError:
                if CurlCffiHttp.config.debug:
                    print(f"⏰ Request timeout (attempt {attempt + 1})")
                continue
            except Exception as e:
                if CurlCffiHttp.config.debug:
                    print(f"❌ Request error: {type(e).__name__}: {str(e)}")
                continue

        # All attempts failed
        if CurlCffiHttp.config.debug:
            print(
                f"❌ All {CurlCffiHttp.config.retry_attempts} attempts failed for {url}"
            )
        return None

    @staticmethod
    def get_sync(url: str) -> Optional[str]:
        """Synchronous method using curl_cffi.requests"""
        try:
            response = curl_requests.get(
                url,
                impersonate=CurlCffiHttp.config.validated_browser,
                timeout=CurlCffiHttp.config.timeout,
                verify=CurlCffiHttp.config.verify_ssl,
                headers=CurlCffiHttp.config.custom_headers,
                cookies=CurlCffiHttp.config.session_cookies,
                proxies=CurlCffiHttp.config.proxies,
            )

            if CurlCffiHttp.config.debug:
                print(f"Response status: {response.status_code}")
                print(f"Response headers: {dict(response.headers)}")

            return response.text if response.status_code == 200 else None

        except Exception as e:
            if CurlCffiHttp.config.debug:
                print(f"❌ Sync request error: {type(e).__name__}: {str(e)}")
            return None
