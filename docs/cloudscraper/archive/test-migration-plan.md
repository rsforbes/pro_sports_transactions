# Test Migration Plan for Cloudscraper Integration

## Overview
This document outlines the changes needed to migrate the test suite from async/aiohttp to sync/cloudscraper.

## Test Changes Required

### 1. Unit Test Changes

#### test_search_responses.py
**Current Structure:**
- Uses `create_mock_coro` fixture for async mocking
- Mocks at `pro_sports_transactions.search.Http.get` level
- Tests are async with `@pytest.mark.asyncio`

**Required Changes:**
```python
# Remove the create_mock_coro fixture entirely
# Replace with simple synchronous mocking

@pytest.fixture
def mock_cloudscraper_response(mocker):
    """Mock cloudscraper response object"""
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.text = ""  # Will be set per test
    return mock_response

@pytest.fixture
def mock_cloudscraper(mocker, mock_cloudscraper_response):
    """Mock cloudscraper instance"""
    mock_scraper = mocker.Mock()
    mock_scraper.get.return_value = mock_cloudscraper_response
    
    # Patch the create_scraper function
    mocker.patch('cloudscraper.create_scraper', return_value=mock_scraper)
    return mock_scraper

@pytest.fixture
def mock_valid_response(mock_cloudscraper, mock_cloudscraper_response):
    """Mock valid search response"""
    with open(
        r"/workspaces/pro_sports_transactions/tests/unit/data/valid_response.html",
        mode="r",
        encoding="utf-8",
    ) as f:
        response_text = f.read()
    
    mock_cloudscraper_response.text = response_text
    return mock_cloudscraper

# Convert async tests to sync
# Change from:
@pytest.mark.asyncio
async def test_valid_results(mock_valid_response):
    search = pst.Search()
    results = await search.get_dataframe()
    
# To:
def test_valid_results(mock_valid_response):
    search = pst.Search()
    # Need to handle async-to-sync conversion in the actual implementation
    results = search.get_dataframe()  # This will need to be wrapped
```

#### Other Unit Tests
**No changes needed for:**
- `test_build_url.py` - Only tests URL building logic
- `test_date_param.py` - Only tests parameter formatting
- `test_transaction_type_param.py` - Only tests parameter logic

These tests don't interact with HTTP calls, so they remain unchanged.

### 2. Integration Test Changes

#### test_search.py
**Current Structure:**
- Makes real HTTP calls using async/await
- Uses `@pytest.mark.asyncio`

**Required Changes:**
```python
# Change from async to sync
# From:
@pytest.mark.asyncio
async def test_search_all_leagues():
    for league in pst.League:
        s = pst.Search(league=league)
        df = await s.get_dataframe()
        
# To:
def test_search_all_leagues():
    for league in pst.League:
        s = pst.Search(league=league)
        df = s.get_dataframe()  # Sync call
```

### 3. API Compatibility Layer

Since the public API is async but cloudscraper is sync, we need a compatibility layer:

```python
# In search.py
class Search:
    # Keep async methods for backwards compatibility
    async def get_dataframe(self) -> DataFrame:
        """Async method for backwards compatibility"""
        # Call sync method in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_dataframe_sync)
    
    def get_dataframe_sync(self) -> DataFrame:
        """Synchronous implementation using cloudscraper"""
        response = Http.get_sync(self.url)
        # ... rest of implementation
    
    # Both methods are public - users can choose which to use
```

### 4. Test Dependencies Updates

**pyproject.toml changes:**
```toml
[tool.poetry.dependencies]
python = "^3.8"  # Update minimum version for cloudscraper
pandas = "^2.0.2"
aiohttp = "^3.8.4"  # Can be removed after migration
cloudscraper = "^3.0.0"  # Add new dependency

[tool.poetry.group.dev.dependencies]
pytest = "^7.3.1"
pytest-asyncio = "^0.21.0"  # Can be removed after full migration
pytest-mock = "^3.10.0"  # Keep for mocking
```

### 5. Phased Migration Approach

To maintain backwards compatibility:

#### Phase 1: Add cloudscraper alongside aiohttp
- Keep existing async API
- Implement cloudscraper in Http class
- Add feature flag to switch implementations
- Keep all existing tests

#### Phase 2: Dual test suite
- Keep existing async tests
- Add new sync test variants
- Test both implementations

#### Phase 3: Deprecate async (optional)
- Mark async methods as deprecated
- Provide migration guide
- Eventually remove async support

### 6. Example Test Migrations

#### Before (Async):
```python
@pytest.mark.asyncio
async def test_lebron_search(mock_valid_response):
    search = pst.Search(player="LeBron James")
    df = await search.get_dataframe()
    assert len(df) > 0
    assert "LeBron James" in df.values
```

#### After (Sync):
```python
def test_lebron_search(mock_valid_response):
    search = pst.Search(player="LeBron James")
    df = search.get_dataframe_sync()  # New sync method
    assert len(df) > 0
    assert "LeBron James" in df.values
```

#### After (Compatibility):
```python
@pytest.mark.asyncio
async def test_lebron_search(mock_valid_response):
    search = pst.Search(player="LeBron James")
    df = await search.get_dataframe()  # Still async, but uses cloudscraper internally
    assert len(df) > 0
    assert "LeBron James" in df.values
```

### 7. Mock Response Differences

**aiohttp Response Mock:**
```python
mock_response = mocker.Mock()
mock_response.status = 200
mock_response.text = mocker.AsyncMock(return_value="HTML content")
```

**cloudscraper Response Mock:**
```python
mock_response = mocker.Mock()
mock_response.status_code = 200  # Note: status_code, not status
mock_response.text = "HTML content"  # Note: property, not method
```

### 8. Error Handling Tests

New error scenarios to test:
```python
def test_cloudflare_challenge_handled():
    """Test that Cloudflare challenges are handled automatically"""
    # Cloudscraper should handle this internally
    search = pst.Search()
    df = search.get_dataframe_sync()
    # Should succeed even with Cloudflare protection

def test_rate_limiting():
    """Test rate limiting with stealth mode"""
    # Configure with stealth delays
    config = CloudscraperConfig(
        enable_stealth=True,
        stealth_min_delay=2.0
    )
    Http.configure(config)
    # Make multiple requests
    # Should not trigger rate limits

def test_captcha_fallback():
    """Test behavior when CAPTCHA is encountered"""
    # Without CAPTCHA solver configured
    # Should raise appropriate exception
```

## Summary

### Minimal Changes Approach (Recommended)
1. Keep async API for backwards compatibility
2. Implement cloudscraper internally with async wrapper
3. Update mocking in tests but keep test structure
4. No changes to tests that don't mock HTTP

### Test Changes Required:
- **Unit tests**: Update mocking fixtures only
- **Integration tests**: May work as-is if API stays async
- **Dependencies**: Add cloudscraper, keep pytest-asyncio for now
- **New tests**: Add cloudscraper-specific scenarios

### No Changes Needed:
- URL building tests
- Parameter formatting tests
- Test data files (HTML responses)
- Test structure and organization