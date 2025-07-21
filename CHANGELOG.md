# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.1.0]: https://github.com/mskarlin/pro_sports_transactions/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/mskarlin/pro_sports_transactions/releases/tag/v1.0.0