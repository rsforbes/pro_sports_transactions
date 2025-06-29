# Claude Code Preferences

## Code Quality Commands

### Using Make (Recommended)
```bash
make help           # Show all available commands
make format         # Format code with black
make lint           # Run pylint and flake8
make test           # Run tests
make coverage       # Run tests with coverage report
make complexity     # Check code complexity
make check          # Run ALL quality checks (use before commit)
make pre-commit     # Alias for 'make check'
```

### Manual Commands
```bash
# Formatting
poetry run black .

# Linting & Quality Checks
poetry run black --check .
poetry run pylint src/pro_sports_transactions
poetry run flake8 --max-complexity=10 .

# Testing with Coverage
poetry run pytest --cov --cov-report=term-missing

# Complexity Analysis
poetry run radon cc src -a  # Cyclomatic complexity
poetry run radon mi src     # Maintainability index
```

## Code Quality Standards

### Target Scores
- **Pylint**: Must maintain 10.00/10 score
- **Flake8**: Zero violations allowed (with documented exceptions)
- **Test Coverage**: Minimum 80% coverage, target 90%+
- **Code Complexity**: McCabe complexity ≤ 10 per function
- **All tests must pass**

### Allowed Exceptions
- **Test complexity**: Test files can exceed C901 (complexity) limits
  - Rationale: Tests often require complex setup/teardown and multiple scenarios
  - This is configured in `.flake8` with proper documentation
- **Coverage exclusions**: Specific patterns excluded from coverage requirements
  - See `pyproject.toml` [tool.coverage.report] for complete list
  - All exclusions must be documented with business justification

### Code Coverage Requirements
- **Minimum Coverage**: 80% overall
- **Target Coverage**: 90% or higher
- **New Code**: Must have 100% coverage unless justified
- **Coverage Reports**: Check before every commit
  ```bash
  poetry run pytest --cov --cov-report=term-missing
  poetry run pytest --cov --cov-report=html  # For detailed HTML report
  ```
- **Uncovered Code**: Must have documented justification
  ```python
  # pragma: no cover - Reason: This is defensive code for external API failures
  ```

### Code Complexity Standards
- **McCabe Complexity**: Maximum 10 per function
- **Cognitive Complexity**: Keep functions simple and readable
- **Function Length**: Prefer functions under 50 lines
- **Class Size**: Prefer classes under 200 lines
- **File Size**: Prefer files under 400 lines

#### Complexity Tools
```bash
# Check complexity with flake8 (already configured)
poetry run flake8 --max-complexity=10 .

# Use radon for detailed metrics (already in dev dependencies)
poetry run radon cc src -a  # Cyclomatic complexity
poetry run radon mi src     # Maintainability index

# Or use the Makefile shortcuts
make complexity           # Basic complexity check
make complexity-detailed  # Full complexity analysis
```

#### Dependencies Already Added
The following tools are already included in `pyproject.toml`:
- `pytest-cov` - for coverage integration
- `radon` - for complexity analysis  
- `flake8-cognitive-complexity` - for cognitive complexity checks

#### Reducing Complexity
When complexity exceeds limits:
1. **Extract Methods**: Break complex functions into smaller ones
2. **Early Returns**: Use guard clauses to reduce nesting
3. **Strategy Pattern**: Replace complex conditionals with polymorphism
4. **Simplify Logic**: Look for ways to reduce conditional branches

Example:
```python
# Bad - High complexity
def process_data(data, mode, validate, transform):
    if mode == 'strict':
        if validate:
            if data is None:
                return None
            else:
                if transform:
                    # ... nested logic
                else:
                    # ... more logic
    elif mode == 'lenient':
        # ... more branches

# Good - Lower complexity
def process_data(data, mode, validate, transform):
    if data is None and validate:
        return None
    
    processor = get_processor(mode)
    return processor.process(data, validate, transform)

def get_processor(mode):
    processors = {
        'strict': StrictProcessor(),
        'lenient': LenientProcessor(),
    }
    return processors.get(mode, DefaultProcessor())
```

### Pre-Commit Quality Gate
Before any commit, ALWAYS run:
```bash
# Using Makefile (recommended)
make check

# Or using poetry directly
poetry run black . && poetry run pylint src/pro_sports_transactions && poetry run flake8 --max-complexity=10 . && poetry run pytest --cov --cov-fail-under=80
```

#### Extended Quality Check (For Major Changes)
```bash
# Using Makefile (recommended)
make check-strict

# Or using poetry directly
poetry run black . && \
poetry run pylint src/pro_sports_transactions && \
poetry run flake8 --max-complexity=10 . && \
poetry run pytest --cov --cov-report=term-missing --cov-fail-under=80 && \
poetry run radon cc src -nc -nd
```

### Configuration Files Reference
All quality standards are enforced through configuration files:
- `.flake8` - Linting rules, complexity limits, and documented exceptions
- `pyproject.toml` - Coverage settings, test configuration, and dependencies
- `Makefile` - Convenient shortcuts for all quality commands
- `.claude/settings.local.json` - Claude Code permissions for automated quality operations

### Claude Code Permissions
The `settings.local.json` file allows Claude Code to automatically perform:

#### Allowed Operations (Immutable/Quality-Improving)
- **Code formatting**: `black` operations to improve readability
- **Quality analysis**: `flake8`, `pylint`, `pytest`, `radon` for reporting
- **Makefile commands**: All quality commands (`make check`, `make format`, etc.)
- **Read-only operations**: File inspection, git status, dependency checking
- **Git file operations**: `git mv` to move files while preserving history

#### Explicitly Denied Operations (Safety)
- **File modifications**: `rm`, `mv`, `cp` - use git equivalents instead
- **Git modifications**: `git commit`, `git push` - maintains explicit control
- **Package changes**: `poetry add/remove` - prevents dependency drift
- **System changes**: `sudo`, `chmod` - prevents system modifications

#### File Operation Best Practices
- **Moving files**: Use `git mv` instead of `mv` to preserve file history
- **Removing files**: Use `git rm` instead of `rm` for proper version control
- **Copying files**: Consider if the copy should be tracked in git

This configuration ensures Claude Code can help with code quality while maintaining safety.

## Code Style Guidelines

### Method Visibility
- **NO PRIVATE METHODS**: Do not use private methods (prefixed with `_` or `__`)
- All methods should be public to improve testability
- Public methods lead to better tests as they don't hide internals
- This applies to all languages:
  - Python: No `_method()` or `__method()`
  - JavaScript/TypeScript: No `#method()` or private keyword
  - Java/C#: Prefer public over private methods
  - Other languages: Follow similar principles

### Rationale
- Public methods are easier to test directly
- No need for complex mocking of private method internals
- Better debugging - all methods are accessible
- Clearer API surface - everything is intentionally public
- Tests serve as better documentation when they test public methods

### Examples

**Good (Public Methods):**
```python
class Http:
    config: Config = Config()
    
    def get_scraper(self):
        return self.create_scraper()
    
    def create_scraper(self):
        # Implementation
```

**Bad (Private Methods):**
```python
class Http:
    _config: Config = Config()
    
    def _get_scraper(self):
        return self._create_scraper()
    
    def _create_scraper(self):
        # Implementation
```

## Additional Preferences

### Configuration
- Avoid unnecessary prefixes (e.g., PST_CONFIG � CONFIG)
- Keep configuration simple and direct

### Testing
- Test public interfaces, not implementation details
- Prefer integration tests over unit tests when reasonable
- Mock external dependencies, not internal methods

### General Code Style
- Explicit is better than implicit
- Simple is better than complex
- Readable code over clever code
- **NO EMOJI**: Never use emoji in code, comments, or output - not all platforms support them
### Code Quality Workflow
1. **ALWAYS run black first** for formatting before running flake8 or pylint
2. **Document all linting disables**: Any flake8 or pylint disabling must include documentation explaining why
   ```python
   # Good - documented disable
   # pylint: disable=too-many-arguments
   # Reason: This function coordinates multiple data sources and requires all parameters
   
   # Bad - no explanation
   # pylint: disable=too-many-arguments
   ```
3. **Document all configuration settings**: Every setting in configuration files must have explanatory comments
   ```ini
   # Good - explains WHY the setting exists
   [flake8]
   # Black uses 88 chars, so we match it for consistency
   max-line-length = 88
   
   # Bad - states the obvious without explaining why
   [flake8]
   # Set max line length
   max-line-length = 88
   ```

### Error Handling Philosophy
- **Comprehensive Classification**: All errors are categorized by type for appropriate handling
- Use specific exception types, not generic Exception
- Document expected error cases
- Provide meaningful error messages
- Run black before any linting to ensure consistent formatting
EOF < /dev/null

### Git Workflow Best Practices
- **Preserve file history**: Always use `git mv` instead of `mv` when moving files
- **Track deletions**: Use `git rm` instead of `rm` when removing files
- **Atomic commits**: Make commits that represent single logical changes
- **Descriptive messages**: Write commit messages that explain WHY, not just what
- **Quality gate**: Always run `make check` before committing

#### Conventional Commit Types
Use these prefixes for commit messages:
- **feat**: new feature for users
- **fix**: bug fix
- **docs**: documentation only changes
- **style**: formatting, missing semi colons, etc; no production code change
- **refactor**: refactoring production code
- **test**: adding missing tests, refactoring tests; no production code change
- **chore**: updating grunt tasks etc; no production code change
- **build**: changes that affect the build system or external dependencies

#### Example Git Operations
```bash
# Good - preserves history
git mv old_file.py new_file.py
git mv src/old_module/ src/new_module/

# Bad - loses history
mv old_file.py new_file.py
mv src/old_module/ src/new_module/

# Good - tracks deletion
git rm deprecated_file.py

# Bad - leaves untracked deletion
rm deprecated_file.py
```
EOF < /dev/null
