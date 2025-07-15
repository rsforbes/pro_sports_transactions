## Development Environment

### Code Quality Commands

#### Emoji
Should never be used as not fully supported on all platforms.

#### Formatting
```bash
poetry run black .
```

#### Linting & Quality Checks
```bash
# Run all quality checks (REQUIRED before committing)
poetry run black --check .
poetry run pylint .
poetry run flake8 .
poetry run pytest
```

#### Testing
```bash
poetry run pytest
poetry run pytest --cov  # With coverage report
```

## Code Quality Standards

### Target Scores
- **Pylint**: Must maintain 10.00/10 score
- **Flake8**: Zero violations allowed
- **Test Coverage**: Maintain current coverage levels
- **All tests must pass**

### Pre-Commit Quality Gate
Before any commit, ALWAYS run:
```bash
poetry run black . && poetry run pylint . && poetry run flake8 . && poetry run pytest
```