In May of 2023, I released a python api that scrapes injury data from prosportstransactions (PST). Everything has been working until recently when a user reported they were getting no data when using the api. After investigation, it appears that PST has implemented Cloudflare, a CDN that blocks bots from scraping data. While CDNs are great for scaling data requests, that it blocks bots prevents the API from working.

Goal:
- Implement changes within the PST library that allow users to continue to access content via cloudflare.
- Changes must support freely available access and not require users to use paid services. 

Note: If paid services are able to successfully bypass cloudflare bot controls, we should be able to do likewise.

## Proposed Solution

### Updated Implementation Strategy

Based on the cloudscraper documentation (v3.0.0), which includes support for:
- Cloudflare v1, v2, v3 JavaScript VM challenges
- Cloudflare Turnstile CAPTCHA replacement
- Automatic 403 error recovery with session refresh
- Built-in stealth mode and proxy rotation
- Python 3.8+ support with async compatibility

### Implementation Plan

#### Phase 1: Cloudscraper Integration (Immediate)
Replace `aiohttp` with `cloudscraper` in the `Http` class:
- **Minimal code changes** - cloudscraper is a drop-in replacement for requests
- **Handles all Cloudflare challenge types** automatically (v1, v2, v3, Turnstile)
- **Built-in stealth mode** to avoid detection
- **Automatic session management** with 403 recovery

#### Phase 2: Async Compatibility Layer
Since our code uses `async/await` with `aiohttp`, we'll need to:
1. Create an async wrapper around cloudscraper (which is sync-based)
2. Use `asyncio.to_thread()` (Python 3.9+) or `loop.run_in_executor()` for async compatibility
3. Maintain the existing async API interface

### Technical Implementation

```python
import cloudscraper
import asyncio
from functools import partial

class Http:
    @staticmethod
    async def get(url):
        # Create scraper with optimal settings for PST
        scraper = cloudscraper.create_scraper(
            browser='chrome',
            interpreter='js2py',  # Default, best compatibility
            delay=5,  # Allow time for challenges
            enable_stealth=True,
            stealth_options={
                'min_delay': 1.0,
                'max_delay': 3.0,
                'human_like_delays': True,
                'randomize_headers': True
            }
        )
        
        # Run synchronous cloudscraper in async context
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            partial(scraper.get, url)
        )
        
        return response.text if response.status_code == 200 else None
```

### Key Advantages of Cloudscraper v3.0.0

1. **Complete Cloudflare Coverage**: Supports all challenge types including the latest v3 VM challenges
2. **No Additional Dependencies**: Just `pip install cloudscraper`
3. **Automatic Recovery**: Handles 403 errors and session refresh automatically
4. **Production Ready**: Well-tested with 100% pass rate for core functionality
5. **Free Solution**: No paid services required

### Implementation Steps

1. **Install cloudscraper**:
   ```bash
   pip install cloudscraper>=3.0.0
   ```

2. **Update Http class** with async wrapper around cloudscraper

3. **Add configuration options** for advanced features if needed:
   - CAPTCHA solving (if Turnstile is encountered)
   - Proxy rotation (if IP blocking occurs)
   - Custom user agents

4. **Test against PST website** to ensure challenges are bypassed

5. **Add error handling** and logging for debugging

### Expected Outcome
The API will transparently handle all Cloudflare protections without any changes to the user's code. The solution will be more robust than browser automation and require fewer dependencies.