# Reference Data

## Browser Fingerprint Data

### Working Browser Configuration (Chrome 138)
From successful manual access to prosportstransactions.com:

```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36
sec-ch-ua: "Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"
sec-ch-ua-arch: "x86"
sec-ch-ua-bitness: "64"
sec-ch-ua-full-version: "138.0.7204.50"
sec-ch-ua-platform: "Windows"
sec-ch-ua-platform-version: "15.0.0"
accept-encoding: gzip, deflate, br, zstd
accept-language: en-US,en;q=0.9
```

### Successful cf_clearance Cookie
```
cf_clearance=yuk1QDs5G23aRROdkuOWRG_bjxbrfQRwJSLxJ3KM5lA-1751119949-1.2.1.1-OgJGCygQmKjn08tEb7ACOy4OMqFWvjcvlZ31og1t3arrGuwt5puxCp.ECMYMuBF68dPq7caZFnYhmKpso0iqqQmBQqWXfLwXiSA6HfR7EbXs5D_U887EcKc7xMpCRHc8VDFdfuy07PA9q7vf5zrkm7xtUVPrNRTs5i4clSsSnlWkP_hOpDgxnWzUxDI9o3Q5rvMtAuzaKbeCOE.7Vv24vy0rPV2q6sBkbLZcVBNNoRLtPkdfdB3vuZ8iSD0jzD5QgiIStW20DUWqfq77A5YNzwnC_i7F9IVGo1fJdwrhIgVQlUnmGk2spvApe35BBmUkGni7._eOjkjbQ9qLXpOm9eRakMo47moey.JjjDmb72OkTSTYWxxFIQMd6pEiFbMO
```

### Challenge Response Headers
```http
cf-mitigated: challenge
server: cloudflare
cf-ray: 956ddeea7c0960a1-ORD
cache-control: private, max-age=0, no-store, no-cache, must-revalidate, post-check=0, pre-check=0
```

## Configuration Templates

### Basic Configuration
```python
config = CloudscraperConfig(
    browser='chrome',
    browser_platform='windows',
    interpreter='js2py',
    delay=15,
    enable_stealth=True,
    debug=True
)
```

### Advanced Configuration with Exact Headers
```python
config = CloudscraperConfig(
    browser='chrome',
    browser_platform='windows',
    browser_mobile=False,
    browser_desktop=True,
    interpreter='js2py',
    delay=15,
    enable_stealth=True,
    stealth_min_delay=1.0,
    stealth_max_delay=3.0,
    stealth_human_like_delays=True,
    stealth_randomize_headers=False,
    stealth_browser_quirks=True,
    allow_brotli=True,
    debug=True,
    custom_headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-arch': '"x86"',
        'sec-ch-ua-bitness': '"64"',
        'sec-ch-ua-full-version': '"138.0.7204.50"',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-platform-version': '"15.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1'
    }
)
```

### Configuration with Valid Session Cookie
```python
config = CloudscraperConfig(
    browser='chrome',
    browser_platform='windows',
    interpreter='js2py',
    delay=15,
    enable_stealth=True,
    debug=True,
    session_cookies={
        'cf_clearance': 'yuk1QDs5G23aRROdkuOWRG_bjxbrfQRwJSLxJ3KM5lA-1751119949-1.2.1.1-...'
    }
)
```

## Challenge Format Examples

### Modern Challenge JavaScript
```javascript
window._cf_chl_opt = {
    cFPWv: 'b'
};

window.__CF$cv$params = {
    r: '956ddeea7c0960a1',
    t: 'MTc1MTEyMDkwNy4wMDAwMDA='
};
```

### Challenge URL Pattern
```
POST /cdn-cgi/challenge-platform/h/b/jsd/r/0.01313896590161113:1751120168:uuGQcGrMYKAbiU7S-5nWc8aWLxMzIT5mqxDn71u5s1Q/956ddeea7c0960a1
Content-Type: text/plain;charset=UTF-8
Content-Length: 16710
```

### Challenge Detection Patterns
```python
# Traditional patterns
r'cpo\.src\s*=\s*[\'\"]/cdn-cgi/challenge-platform/\S+orchestrate/jsch/v3'
r'window\._cf_chl_ctx\s*='
r'<form[^>]*id="challenge-form"[^>]*action="[^"]*__cf_chl_rt_tk='

# Modern patterns (added)
r'window\._cf_chl_opt\s*='
'Just a moment' in resp.text
'/challenge-platform/' in resp.text
resp.headers.get('cf-mitigated') == 'challenge'
```

## Key Research Insights

### Critical Quotes on TLS Fingerprinting
> "Of all the passive bot detection techniques of Cloudflare, TLS and HTTP/2 fingerprinting are the most technically challenging to control" 

> "Cloudflare's Canvas fingerprinting relies heavily on moving parts from software and hardware"

> "Most Cloudflare solvers opt for static bypass, while others employ headless browsers. Unfortunately, even their paid tiers often fail to keep up with Cloudflare's evolving ecosystem"

### Detection Hierarchy (Most Important First)
1. **TLS Fingerprinting** - Cipher suites, extensions, TLS version negotiation
2. **HTTP/2 Fingerprinting** - Binary frame layer parameters
3. **Canvas Fingerprinting** - Hardware/software dependent rendering signatures
4. **Event Tracking** - Mouse movements, clicks, keyboard input patterns
5. **Environment API Querying** - Browser-specific JavaScript properties
6. **Automated Browser Detection** - Selenium/WebDriver property detection

## File Mapping Reference

### Core Implementation Files
```
src/pro_sports_transactions/search.py           # Main cloudscraper integration
├── CloudscraperConfig class                    # Configuration management
├── Http.configure() method                     # Setup and patching
└── async/sync compatibility layer              # Backward compatibility

temp_cloudscraper/cloudscraper/cloudflare_v3_patched.py  # Enhanced V3 handler
├── is_V3_Challenge() - Modern detection
├── parse_js_object_manually() - JS object parsing
├── handle_modern_challenge() - Modern challenge logic
└── generate_v3_challenge_payload() - JSON payload support

examples/test_cloudscraper.py                   # Usage demonstration
```

### Documentation Structure
```
docs/cloudscraper/
├── CLOUDSCRAPER_WORK_SUMMARY.md               # Main entry point
├── TECHNICAL_ANALYSIS.md                      # Deep technical details
├── REFERENCE_DATA.md                          # This file - quick lookup
└── cloudscraper-testing.md                    # Complete test log
```

### Dependency Configuration
```toml
# pyproject.toml
[tool.poetry.dependencies]
cloudscraper = {git = "https://github.com/VeNoMouS/cloudscraper.git", rev = "refs/pull/295/head"}

# Key versions tested
python = "^3.11"
aiohttp = "^3.8.4"  # Maintained for compatibility
```

## Test Configuration Matrix

| Test # | Browser | Platform | Interpreter | Delay | Stealth | Result | Key Feature |
|--------|---------|----------|-------------|-------|---------|--------|-------------|
| 1-3 | chrome | windows | js2py | 5-10 | enabled | TIMEOUT | Standard configs |
| 6 | chrome | windows | js2py | 15 | enabled | TIMEOUT | Exact headers |
| 7 | chrome | windows | js2py | 15 | enabled | TIMEOUT | Valid cf_clearance |
| 8 | chrome | windows | js2py | 20 | enabled | TIMEOUT | Enhanced v3 + TLS rotation |
| 9-10 | chrome | windows | js2py | 15-30 | varies | FAIL | PR #295 session refresh |
| 11 | chrome | windows | js2py | 20 | enabled | TIMEOUT | PR #283 extra headers |
| 12 | chrome | windows | js2py | 20 | enabled | FAIL | **Patched V3 handler** |

## Alternative Library References

### Browser Automation Options
```python
# Playwright with stealth
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# Puppeteer equivalent
import pyppeteer
```

### TLS-Focused Libraries
```python
# curl_cffi - curl-based HTTP client
import curl_cffi

# tls-client - Go TLS implementation
import tls_client

# requests-html - PyQt-based browser
import requests_html
```

### Next Implementation Targets
1. **Playwright + stealth**: Most comprehensive solution
2. **curl_cffi**: Better TLS without browser overhead  
3. **Hybrid approach**: Browser tokens + programmatic access

---

*Reference data compiled from 12 systematic tests and comprehensive browser analysis of prosportstransactions.com Cloudflare protection.*