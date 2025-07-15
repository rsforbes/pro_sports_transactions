# Performance Testing Scripts

This directory contains performance testing scripts for the Pro Sports Transactions API.

## Performance Test Script

The `performance_test.py` script measures:
- Initial connection time
- Cloudflare bypass time (if encountered)
- Page loading times for 5 consecutive pages
- Whether Cloudflare interferes with each page request
- Session reuse metrics

### Setup

Before running the performance test for the first time, you need to install Playwright browsers:

```bash
# Option 1: Run the setup script
python scripts/setup_performance_test.py

# Option 2: Install manually (choose one or more browsers)
playwright install chromium    # Recommended for consistency
playwright install firefox     # Alternative browser
playwright install webkit      # Safari engine
```

### Running the Test

```bash
# Default (uses Chromium)
python scripts/performance_test.py

# Use a specific browser
python scripts/performance_test.py --browser firefox
python scripts/performance_test.py --browser webkit
```

### Browser Options

- **chromium** (default): Best for consistency across platforms, closest to Chrome/Edge
- **firefox**: Mozilla Firefox engine, good alternative option
- **webkit**: Safari's engine, useful for testing Safari-like behavior

### Output

The script will display:
- Real-time progress for each page load
- Performance metrics for each page
- Summary statistics including:
  - Average navigation and load times
  - Cloudflare interference analysis
  - Session reuse effectiveness

### Requirements

- Python 3.7+
- playwright package (installed via pip/poetry)
- Playwright Chromium browser (installed via setup script or manually)

### Notes for End Users

The Playwright browser installation is a one-time setup that downloads the browser binaries. This is separate from the Python package installation and is required for all users who want to run performance tests.