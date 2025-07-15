# Performance Architecture for Pro Sports Transactions API

## Current Performance Issues

1. **Browser Lifecycle**: Each search request creates a new browser instance, navigates, extracts data, then closes the browser
2. **Cloudflare Challenge**: Every request faces Cloudflare challenge due to lack of cookie persistence
3. **No Concurrency**: Searches are performed sequentially, even when fetching multiple pages
4. **Resource Overhead**: Creating/destroying browser instances is expensive (~2-3 seconds per request)

## Proposed Architecture Options

### Option 1: Browser Session Pool (Recommended)

**Design**: Maintain a pool of persistent browser contexts that can be reused across requests.

```python
class BrowserPool:
    def __init__(self, pool_size=3, browser_type="chromium"):
        self.pool = asyncio.Queue(maxsize=pool_size)
        self.browser_type = browser_type
        
    async def acquire(self) -> BrowserContext:
        """Get a browser context from the pool"""
        
    async def release(self, context: BrowserContext):
        """Return a browser context to the pool"""
```

**Pros**:
- Cloudflare cookies persist across requests
- Eliminates browser startup/shutdown overhead
- Can handle concurrent requests efficiently
- Pool size can be tuned based on load

**Cons**:
- More complex to implement
- Need to handle stale contexts/crashes
- Memory usage scales with pool size

### Option 2: Single Shared Browser Instance

**Design**: Use one browser instance with multiple contexts for isolation.

```python
class SharedBrowserClient:
    def __init__(self):
        self.browser = None
        self._lock = asyncio.Lock()
        
    async def get_context(self) -> BrowserContext:
        """Create a new context from shared browser"""
```

**Pros**:
- Simpler than pool approach
- Lower memory footprint
- Easier to manage lifecycle
- Contexts are isolated (cookies/storage separate)

**Cons**:
- If browser process crashes, all contexts fail (but we can auto-restart)
- May bottleneck under high concurrency (but contexts can run in parallel)
- Context creation still has overhead (~100-200ms)

**Single Point of Failure Clarification**:
- The "failure" is just the browser process crashing
- Impact: Current requests fail, but we can detect and restart the browser
- Not really cascading - just a temporary disruption
- With proper error handling, this is manageable

### Option 3: Batch Request API

**Design**: Accept multiple search parameters and execute them concurrently.

```python
class BatchSearch:
    async def search_many(self, searches: List[SearchParams]) -> List[SearchResult]:
        """Execute multiple searches concurrently"""
        
    async def search_pages(self, base_search: SearchParams, page_count: int) -> List[SearchResult]:
        """Fetch multiple pages of the same search concurrently"""
```

**Pros**:
- Massive performance gains for multi-page requests
- Can combine with session pooling
- Natural fit for pagination use cases

**Cons**:
- Breaking API change
- Requires client code updates
- May hit rate limits

## Recommended Implementation Plan (Revised)

### Phase 1: Shared Browser Instance (Option 2)
Start simple with a single shared browser that creates contexts on demand.

```python
# Can maintain existing interface
search = Search(league=League.NBA)
result = await search.get_dict()  # Uses shared browser internally
```

**Benefits**:
- Quick to implement and test
- Can keep existing interface initially
- Immediate performance gains from session reuse
- Learn operational characteristics

### Phase 2: Browser Pool (Option 1)
Upgrade to pool when we understand usage patterns.

```python
# Still works with existing interface
search = Search(league=League.NBA)
result = await search.get_dict()  # Now uses pool internally
```

**Benefits**:
- Better concurrency handling
- More resilient to failures
- Can tune pool size based on Phase 1 learnings

### Phase 3: Batch API (Option 3)
Add high-performance batch operations.

```python
# New API for power users
async with SearchSession() as session:
    # Fetch 5 pages concurrently
    results = await session.search_pages(params, count=5)
```

**Benefits**:
- Massive performance for multi-page queries
- Opt-in for users who need it
- Can coexist with simple API

## Interface Design Considerations

### Option A: Keep Existing Interface (Hidden Performance)
```python
# User code stays the same
search = Search(league=League.NBA)
result = await search.get_dict()

# But internally uses shared resources
# Pro: No breaking changes
# Con: Less control for users
```

### Option B: New Performance-First Interface
```python
# Explicit session management
async with SearchSession() as session:
    result = await session.search(league=League.NBA)
    
# Pro: Clear performance benefits
# Con: Breaking change
```

### Option C: Hybrid Approach
```python
# Simple API (uses shared browser)
result = await Search.quick(league=League.NBA)

# Advanced API (full control)
async with SearchSession() as session:
    results = await session.batch_search([...])
```

## Performance Targets

Based on current measurements:
- **Current**: ~15-20s per page (new browser each time)
- **With Session Reuse**: ~3-5s per page (after first request)
- **With Batch Operations**: ~5-10s for 5 pages (concurrent execution)

## API Design Examples

### New Session-Based API
```python
from pro_sports_transactions import SearchSession, SearchParams

async def fetch_recent_transactions():
    async with SearchSession() as session:
        # First request - may hit Cloudflare
        page1 = await session.search(
            league=League.NBA,
            start_date=date.today() - timedelta(30),
            end_date=date.today()
        )
        
        # Subsequent requests - bypass Cloudflare
        page2 = await session.search(
            league=League.NBA,
            starting_row=25
        )
        
        return [page1, page2]
```

### Batch API
```python
async def fetch_all_pages():
    async with SearchSession() as session:
        # Fetch 5 pages concurrently
        results = await session.search_pages(
            SearchParams(
                league=League.NBA,
                transaction_types=[TransactionType.Movement],
                start_date=date.today() - timedelta(30)
            ),
            page_count=5,
            page_size=25
        )
        return results
```

### Legacy Compatibility
```python
# Old code continues to work
search = Search(league=League.NBA)
result = await search.get_dict()  # Uses pool internally
```

## Implementation Considerations

1. **Resource Management**
   - Pool size limits
   - Timeout handling
   - Graceful shutdown

2. **Error Handling**
   - Browser crashes
   - Network failures
   - Cloudflare blocks

3. **Configuration**
   - Pool size
   - Timeout values
   - Retry policies
   - Browser options

4. **Monitoring**
   - Pool utilization
   - Request latency
   - Cloudflare hit rate
   - Error rates

## Migration Strategy

1. **Phase 1**: Implement new SearchSession API alongside existing code
2. **Phase 2**: Add deprecation warnings to old API
3. **Phase 3**: Update documentation and examples
4. **Phase 4**: Remove old implementation (major version bump)

## Updated Implementation Strategy

Based on your feedback, here's the refined approach:

### Build Order: 2 → 1 → 3

1. **Start with Option 2** (Shared Browser)
   - Simplest to implement
   - Proves the concept
   - Can maintain existing interface or go fresh
   
2. **Evolve to Option 1** (Browser Pool)
   - Natural progression from shared browser
   - Add when we need better concurrency
   - Minimal code changes from Option 2

3. **Add Option 3** (Batch API)
   - Premium performance feature
   - Built on top of pool infrastructure
   - New interface for power users

### Interface Decision: Keep It Simple, Change the Implementation

We can maintain the exact same interface while swapping implementations:

**Strategy: Backend Abstraction Pattern**

```python
# search.py - User-facing interface (UNCHANGED)
class Search:
    def __init__(self, league=League.NBA, **kwargs):
        self.league = league
        # ... same as before
        
    async def get_dict(self):
        # Delegates to current backend
        return await backend.search(self._build_params())
    
    async def get_json(self):
        # Same interface, different engine
        return json.dumps(await self.get_dict())

# backend.py - Swappable implementations
class Backend(ABC):
    @abstractmethod
    async def search(self, params):
        pass

class LegacyBackend(Backend):
    """Current implementation - new browser each time"""
    async def search(self, params):
        client = SimplePlaywrightClient()
        return await client.get_page_content(params.url)

class SharedBrowserBackend(Backend):
    """Option 2 - Shared browser instance"""
    def __init__(self):
        self.browser = None
        self._lock = asyncio.Lock()
        
    async def search(self, params):
        context = await self._get_or_create_context()
        return await self._search_with_context(context, params)

class PooledBrowserBackend(Backend):
    """Option 1 - Browser pool"""
    def __init__(self, pool_size=3):
        self.pool = BrowserPool(size=pool_size)
        
    async def search(self, params):
        async with self.pool.acquire() as context:
            return await self._search_with_context(context, params)
```

**Configuration-Based Selection**

```python
# config.py or environment variable
BACKEND_TYPE = os.getenv("PST_BACKEND", "shared")  # or "legacy", "pooled"

# Factory pattern
def create_backend():
    if BACKEND_TYPE == "legacy":
        return LegacyBackend()
    elif BACKEND_TYPE == "shared":
        return SharedBrowserBackend()
    elif BACKEND_TYPE == "pooled":
        return PooledBrowserBackend()
    
# Global backend instance
backend = create_backend()
```

**Benefits**:
- Zero breaking changes
- Users don't need to know about backends
- Can A/B test different implementations
- Easy rollback if issues arise
- Can choose backend based on environment

### Flexibility Benefits

Having all three options gives us:
- **Development flexibility**: Start simple, evolve as needed
- **Deployment flexibility**: Can choose based on server resources
- **User flexibility**: Simple or advanced APIs
- **Testing flexibility**: Can benchmark all approaches

## Implementation Examples

### How Users Continue Using the API (Unchanged)

```python
from pro_sports_transactions import Search, League

# Exactly the same as before
search = Search(
    league=League.NBA,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31)
)

# Still works the same
result = await search.get_dict()
print(f"Found {len(result['transactions'])} transactions")

# Multiple searches still create multiple Search objects
for page in range(5):
    search = Search(league=League.NBA, starting_row=page * 25)
    data = await search.get_dict()
    # Under the hood, this reuses browser contexts!
```

### How We Switch Implementations

```python
# Option 1: Environment variable
# PST_BACKEND=pooled python my_script.py

# Option 2: Programmatic configuration
from pro_sports_transactions import config
config.set_backend("pooled")  # or "shared", "legacy"

# Option 3: Runtime switching (for testing)
from pro_sports_transactions.backends import use_backend
use_backend("shared")  # Switch to shared browser
results1 = await search.get_dict()

use_backend("pooled")  # Switch to pooled
results2 = await search.get_dict()
```

### Progressive Enhancement Path

```python
# Stage 1: Start with legacy (current behavior)
backend = LegacyBackend()  # Each request = new browser

# Stage 2: Move to shared (immediate wins)
backend = SharedBrowserBackend()  # Reuse browser, new contexts

# Stage 3: Graduate to pooled (scale better)
backend = PooledBrowserBackend(size=5)  # Multiple browsers, managed pool

# Stage 4: Add batch capability (same interface!)
# Users can still use Search class, but we batch internally
results = await asyncio.gather(
    Search(league=League.NBA, page=0).get_dict(),
    Search(league=League.NBA, page=1).get_dict(),
    Search(league=League.NBA, page=2).get_dict(),
)
# Behind the scenes, these could share contexts or run in parallel
```

## Next Steps

1. Create `backends.py` with abstract base class
2. Implement `SharedBrowserBackend` (Option 2) first
3. Modify `Search` class to use backend pattern
4. Add configuration/environment variable support
5. Create performance benchmarks comparing backends
6. Implement `PooledBrowserBackend` (Option 1) when ready
7. Add batch optimization as backend enhancement