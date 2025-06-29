# Cloudscraper Configuration Options for PST API

## Overview
This document details the configuration options for integrating cloudscraper into the ProSportsTransactions API to bypass Cloudflare protection.

## Configuration Implementation

### 1. Basic Configuration Class

```python
from dataclasses import dataclass
from typing import Optional, Dict, List
import os

@dataclass
class CloudscraperConfig:
    """Configuration for cloudscraper integration"""
    
    # Browser emulation
    browser: str = 'chrome'  # 'chrome' or 'firefox'
    browser_platform: Optional[str] = None  # 'windows', 'linux', 'darwin', 'android', 'ios'
    browser_mobile: bool = False
    browser_desktop: bool = True
    
    # JavaScript interpreter
    interpreter: str = 'js2py'  # 'js2py', 'nodejs', 'native', 'v8'
    
    # Challenge handling
    delay: int = 5  # Seconds to wait for challenges
    disable_cloudflare_v1: bool = False
    disable_cloudflare_v2: bool = False
    disable_cloudflare_v3: bool = False
    disable_turnstile: bool = False
    
    # Stealth mode
    enable_stealth: bool = True
    stealth_min_delay: float = 1.0
    stealth_max_delay: float = 3.0
    stealth_human_like_delays: bool = True
    stealth_randomize_headers: bool = True
    stealth_browser_quirks: bool = True
    
    # Performance
    allow_brotli: bool = True
    debug: bool = False
    
    # CAPTCHA solving (optional)
    captcha_provider: Optional[str] = None  # '2captcha', 'anticaptcha', etc.
    captcha_api_key: Optional[str] = None
    
    # Proxy configuration (optional)
    rotating_proxies: Optional[List[str]] = None
    proxy_rotation_strategy: str = 'sequential'  # 'sequential', 'random', 'smart'
    proxy_ban_time: int = 300  # seconds
    
    # TLS/SSL configuration
    ecdhCurve: str = 'prime256v1'  # or 'secp384r1' for some servers
    cipherSuite: Optional[str] = None
    server_hostname: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'CloudscraperConfig':
        """Create config from environment variables"""
        config = cls()
        
        # Browser settings
        if browser := os.getenv('BROWSER'):
            config.browser = browser
        if platform := os.getenv('BROWSER_PLATFORM'):
            config.browser_platform = platform
            
        # Stealth mode
        if stealth := os.getenv('ENABLE_STEALTH'):
            config.enable_stealth = stealth.lower() == 'true'
            
        # Debug mode
        if debug := os.getenv('DEBUG'):
            config.debug = debug.lower() == 'true'
            
        # CAPTCHA settings
        if provider := os.getenv('CAPTCHA_PROVIDER'):
            config.captcha_provider = provider
            config.captcha_api_key = os.getenv('CAPTCHA_API_KEY')
            
        # Proxy settings
        if proxies := os.getenv('PROXIES'):
            config.rotating_proxies = proxies.split(',')
            
        return config
```

### 2. Integration with Http Class

```python
import cloudscraper
import asyncio
from functools import partial
from typing import Optional

class Http:
    # Class-level configuration
    config: CloudscraperConfig = CloudscraperConfig()
    scraper_instance: Optional[cloudscraper.CloudScraper] = None
    
    @classmethod
    def configure(cls, config: CloudscraperConfig):
        """Configure cloudscraper settings"""
        cls.config = config
        cls.scraper_instance = None  # Force recreation with new config
    
    @classmethod
    def get_scraper(cls) -> cloudscraper.CloudScraper:
        """Get or create scraper instance with configuration"""
        if cls.scraper_instance is None:
            # Build browser config
            browser_config = {
                'browser': cls.config.browser,
                'platform': cls.config.browser_platform,
                'mobile': cls.config.browser_mobile,
                'desktop': cls.config.browser_desktop,
            }
            # Remove None values
            browser_config = {k: v for k, v in browser_config.items() if v is not None}
            
            # Build stealth options
            stealth_options = {
                'min_delay': cls.config.stealth_min_delay,
                'max_delay': cls.config.stealth_max_delay,
                'human_like_delays': cls.config.stealth_human_like_delays,
                'randomize_headers': cls.config.stealth_randomize_headers,
                'browser_quirks': cls.config.stealth_browser_quirks,
            }
            
            # Build CAPTCHA config if provided
            captcha_config = None
            if cls.config.captcha_provider:
                captcha_config = {
                    'provider': cls.config.captcha_provider,
                }
                if cls.config.captcha_api_key:
                    if cls.config.captcha_provider == '2captcha':
                        captcha_config['api_key'] = cls.config.captcha_api_key
                    elif cls.config.captcha_provider == 'anticaptcha':
                        captcha_config['api_key'] = cls.config.captcha_api_key
                    # Add other providers as needed
            
            # Build proxy options
            proxy_options = None
            if cls.config.rotating_proxies:
                proxy_options = {
                    'rotation_strategy': cls.config.proxy_rotation_strategy,
                    'ban_time': cls.config.proxy_ban_time,
                }
            
            # Create scraper
            cls.scraper_instance = cloudscraper.create_scraper(
                browser=browser_config,
                interpreter=cls.config.interpreter,
                delay=cls.config.delay,
                
                # Challenge toggles
                disableCloudflareV1=cls.config.disable_cloudflare_v1,
                disableCloudflareV2=cls.config.disable_cloudflare_v2,
                disableCloudflareV3=cls.config.disable_cloudflare_v3,
                disableTurnstile=cls.config.disable_turnstile,
                
                # Stealth mode
                enable_stealth=cls.config.enable_stealth,
                stealth_options=stealth_options if cls.config.enable_stealth else None,
                
                # Performance
                allow_brotli=cls.config.allow_brotli,
                debug=cls.config.debug,
                
                # CAPTCHA
                captcha=captcha_config,
                
                # Proxies
                rotating_proxies=cls.config.rotating_proxies,
                proxy_options=proxy_options if cls.config.rotating_proxies else None,
                
                # TLS/SSL
                ecdhCurve=cls.config.ecdhCurve,
                cipherSuite=cls.config.cipherSuite,
                server_hostname=cls.config.server_hostname,
            )
            
        return cls.scraper_instance
    
    @staticmethod
    async def get(url):
        """Async wrapper around cloudscraper"""
        scraper = Http.get_scraper()
        
        # Run synchronous cloudscraper in async context
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            partial(scraper.get, url)
        )
        
        if Http.config.debug:
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")
        
        return response.text if response.status_code == 200 else None
```

### 3. Usage Examples

```python
# Example 1: Basic usage with defaults
from pro_sports_transactions import Search, League

# Uses default configuration
search = Search(
    league=League.NBA,
    player="LeBron James"
)
results = await search.get_dataframe()

# Example 2: Custom configuration
from pro_sports_transactions.search import Http, CloudscraperConfig

# Configure with custom settings
config = CloudscraperConfig(
    browser='firefox',
    browser_platform='windows',
    enable_stealth=True,
    debug=True,
    delay=10,  # More time for complex challenges
    interpreter='nodejs'  # Try different JS interpreter
)
Http.configure(config)

# Now all searches will use this configuration
search = Search(league=League.NBA)
results = await search.get_dataframe()

# Example 3: Environment-based configuration
# Set environment variables:
# BROWSER=chrome
# ENABLE_STEALTH=true
# DEBUG=true
# CAPTCHA_PROVIDER=2captcha
# CAPTCHA_API_KEY=your_key_here

config = CloudscraperConfig.from_env()
Http.configure(config)

# Example 4: Proxy configuration
config = CloudscraperConfig(
    rotating_proxies=[
        'http://proxy1.example.com:8080',
        'http://proxy2.example.com:8080',
    ],
    proxy_rotation_strategy='smart',
    proxy_ban_time=600
)
Http.configure(config)

# Example 5: CAPTCHA solving for Turnstile
config = CloudscraperConfig(
    captcha_provider='2captcha',
    captcha_api_key='your_2captcha_api_key',
    disable_turnstile=False  # Ensure Turnstile handling is enabled
)
Http.configure(config)
```

### 4. Recommended Configuration

Based on ProSportsTransactions website characteristics:

```python
# Recommended configuration
RECOMMENDED_CONFIG = CloudscraperConfig(
    # Browser emulation
    browser='chrome',  # Most common browser
    browser_platform='windows',  # Most common platform
    browser_desktop=True,
    browser_mobile=False,
    
    # JavaScript handling
    interpreter='js2py',  # Best compatibility
    delay=5,  # Standard delay for challenges
    
    # Enable all challenge types
    disable_cloudflare_v1=False,
    disable_cloudflare_v2=False,
    disable_cloudflare_v3=False,
    disable_turnstile=False,
    
    # Stealth mode (important for sports data sites)
    enable_stealth=True,
    stealth_min_delay=1.0,
    stealth_max_delay=3.0,
    stealth_human_like_delays=True,
    stealth_randomize_headers=True,
    
    # Performance
    allow_brotli=True,
    debug=False,  # Enable for troubleshooting
)
```

### 5. Troubleshooting Configurations

If the default configuration doesn't work, try these alternatives:

```python
# Configuration 1: Maximum compatibility
COMPAT_CONFIG = CloudscraperConfig(
    interpreter='nodejs',  # Requires Node.js installed
    delay=10,  # More time for challenges
    enable_stealth=True,
    stealth_max_delay=6.0,  # Slower but more human-like
)

# Configuration 2: For rate limiting issues
RATE_LIMIT_CONFIG = CloudscraperConfig(
    enable_stealth=True,
    stealth_min_delay=3.0,
    stealth_max_delay=8.0,
    stealth_human_like_delays=True,
    # Add proxies if available
    rotating_proxies=['proxy1', 'proxy2'],
    proxy_rotation_strategy='smart',
)

# Configuration 3: For complex challenges
COMPLEX_CONFIG = CloudscraperConfig(
    interpreter='nodejs',
    delay=15,  # Maximum delay
    ecdhCurve='secp384r1',  # Some sites need this
    debug=True,  # See what's happening
)

# Configuration 4: Minimal detection footprint
MINIMAL_CONFIG = CloudscraperConfig(
    browser='firefox',  # Less common for bots
    browser_platform='linux',
    enable_stealth=True,
    stealth_browser_quirks=True,
    stealth_randomize_headers=True,
)
```

### 6. Integration with Existing Code

The configuration system is designed to be backwards compatible:

1. **No configuration**: Uses sensible defaults
2. **Global configuration**: Set once at application startup
3. **Per-request configuration**: Could be extended if needed
4. **Environment-based**: For deployment flexibility

### 7. Monitoring and Logging

```python
import logging

# Enable cloudscraper debug logging
if config.debug:
    logging.basicConfig(level=logging.DEBUG)
    cloudscraper_logger = logging.getLogger('cloudscraper')
    cloudscraper_logger.setLevel(logging.DEBUG)
```

## Summary

The configuration system provides:
- **Flexibility**: Multiple ways to configure
- **Sensible defaults**: Works out of the box
- **Advanced options**: For challenging scenarios
- **Environment support**: For production deployments
- **Backwards compatibility**: No breaking changes to API