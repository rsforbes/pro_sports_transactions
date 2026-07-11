# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CI workflow running the unit test suite across Python 3.11–3.14 on every pull request
- Python version Trove classifiers (3.11–3.14) advertising the supported release range
- Dev container persists Claude Code history and memory across rebuilds (named volume on `~/.claude`) and installs the GitHub CLI via the `github-cli` dev container feature

### Changed
- Migrated the project toolchain from Poetry to [uv](https://docs.astral.sh/uv/) (`uv.lock` replaces `poetry.lock`; build backend is now hatchling)
- Replaced black, flake8, isort, and pylint with [Ruff](https://docs.astral.sh/ruff/) for formatting and linting
- Raised the pandas floor to `>=2.2.2` (the first release with numpy 2 support) so the declared minimum resolves against modern numpy; a `--resolution lowest-direct` CI leg now guards it

### Fixed
- Unit tests resolve their HTML response fixtures relative to the test file instead of a hardcoded absolute path, so the suite runs outside the original dev container (e.g. in CI)

## [1.1.2] - 2026-02-07

### Fixed
- Resolved "Can not decode content-encoding: br" Brotli decoding error in `UnflareRequestHandler` by adding `Accept-Encoding: gzip, deflate, br` header to all outbound requests ([#11](https://github.com/rsforbes/pro_sports_transactions/issues/11))
- Added `aiohttp.ClientTimeout` (120s) to all HTTP sessions to prevent requests from hanging indefinitely
- Non-200 HTTP responses are now logged with status code and response body instead of failing silently

### Changed
- Replaced all `print()` statements in `UnflareRequestHandler` with Python `logging` module
- Added `NullHandler` to package logger so consumers control log output
- Fixed integration test service availability check (use correct HTTP method and target URL)

### Added
- Example script (`examples/unflare_search.py`) demonstrating Unflare handler usage

### Security
- Bumped brotli from ^1.0.9 to ^1.2.0

## [1.1.1] - 2025-08-15

### Fixed
- Test: Updated test_unflare_handler_integration timeout from 1s to 5s.

### Security 
- Bumped aiohttp from 3.8.4 -> 3.12.14

## [1.1.0] - 2025-07-21

### Added

#### 🚀 Request Handler Architecture
- New extensible request handler system with abstract base class `RequestHandler`
- `DirectRequestHandler` for standard HTTP requests with configurable timeouts
- `UnflareRequestHandler` for Cloudflare bypass with intelligent cookie caching and retry logic
- Optional `request_handler` parameter in `Search` constructor (backward compatible)

#### ⚡ Performance Testing Framework
- Comprehensive performance benchmarks with configurable thresholds
- Performance configuration in `pyproject.toml` (cache speedup 10x, timeouts, etc.)
- New performance test suite validating response times and cache efficiency

#### 🧪 Enhanced Testing
- Added pytest markers for unit, integration, and performance tests
- Expanded test coverage with 58 new unit tests
- Service availability checks for integration tests
- Strict marker enforcement in pytest configuration

### Changed

#### 📚 Documentation
- Complete README overhaul with Cloudflare/Unflare setup instructions
- Added detailed troubleshooting section
- Documented all new handlers with practical examples
- Added performance testing documentation and configuration guide

#### 🔧 Development Environment
- Enhanced dev container setup with Poetry and development tools
- VS Code configuration for Black, Pylint, Flake8, and Pylance
- Automated dependency installation via post-create command

### Improved

#### 🛡️ Code Quality
- Achieved 10/10 pylint score with targeted local disables
- Added missing module docstrings throughout codebase
- Replaced broad exception catches with specific exception types
- Fixed pytest fixture naming to avoid warnings

### Technical Details

- **100% Backward Compatibility**: All existing APIs remain unchanged
- **New Dependencies**: Added pylint to dev dependencies
- **Configuration**: Added performance thresholds and pytest markers to `pyproject.toml`

## [1.0.0] - 2024-XX-XX

### Added
- Initial release with core functionality
- Support for MLB, NBA, NHL, NFL, and MLS transactions
- Basic search capabilities with team and date filtering
- Transaction type filtering
- Cache support for improved performance

[1.1.2]: https://github.com/rsforbes/pro_sports_transactions/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/rsforbes/pro_sports_transactions/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/rsforbes/pro_sports_transactions/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/rsforbes/pro_sports_transactions/releases/tag/v1.0.0