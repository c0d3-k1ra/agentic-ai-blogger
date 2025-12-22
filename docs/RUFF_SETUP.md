# Ruff Configuration

This project uses [Ruff](https://docs.astral.sh/ruff/) - an extremely fast Python linter and formatter written in Rust, serving as a drop-in replacement for multiple tools including Flake8, isort, pydocstyle, and more.

## Why Ruff?

- **Speed**: 10-100x faster than traditional Python linters
- **All-in-One**: Replaces Flake8, isort, Black, pydocstyle, and more
- **Auto-Fix**: Automatically fixes many issues
- **Modern**: Built with Rust for maximum performance
- **Compatible**: Drop-in replacement for existing tools

## Configuration Summary

- **Location**: `pyproject.toml` under `[tool.ruff]`
- **Target Version**: Python 3.8+
- **Line Length**: 88 characters
- **Selected Rules**: ~700+ rules enabled
- **Auto-Fix**: Enabled via pre-commit hooks
- **Scope**: Entire project (`src/`, `tests/`)

## Configuration File

The configuration in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 88
target-version = "py38"

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "N",      # pep8-naming
    "UP",     # pyupgrade
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "SIM",    # flake8-simplify
    "TCH",    # flake8-type-checking
    "Q",      # flake8-quotes
]

ignore = [
    "E501",   # line too long (handled by formatter)
    "B008",   # do not perform function calls in argument defaults
    "B904",   # raise from None/Exception
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
```

## Usage

### Check for Issues

```bash
# Check all files
poetry run ruff check .

# Check specific directory
poetry run ruff check src/

# Check specific file
poetry run ruff check src/database/db.py

# Check with auto-fix
poetry run ruff check . --fix
```

### Format Code

```bash
# Format all files
poetry run ruff format .

# Format specific directory
poetry run ruff format src/

# Format specific file
poetry run ruff format src/database/db.py

# Check formatting without modifying
poetry run ruff format --check .
```

### Combined Workflow

```bash
# Run both linting and formatting
poetry run ruff check . --fix && poetry run ruff format .
```

## What Gets Checked

**Included**: ✅
- `src/` directory (all Python files)
- `tests/` directory (all Python files)
- All `.py` files in project root

**Automatically Excluded**: ❌
- `.venv/`, `venv/` - Virtual environments
- `.git/` - Git directory
- `__pycache__/` - Python cache
- `*.pyc` - Compiled Python files
- `.pytest_cache/` - Pytest cache
- `.ruff_cache/` - Ruff cache

## Rule Categories

### Enabled Rule Sets

1. **E, W (pycodestyle)** - Style guide enforcement
   - Whitespace issues
   - Indentation problems
   - Line length (warnings only)

2. **F (Pyflakes)** - Logical errors
   - Unused imports
   - Undefined names
   - Invalid syntax

3. **I (isort)** - Import sorting
   - Alphabetical ordering
   - Section grouping
   - Consistent formatting

4. **N (pep8-naming)** - Naming conventions
   - Class names (CamelCase)
   - Function names (snake_case)
   - Constant names (UPPER_CASE)

5. **UP (pyupgrade)** - Modern Python syntax
   - Type hint improvements
   - String formatting upgrades
   - Deprecated syntax fixes

6. **B (flake8-bugbear)** - Bug detection
   - Common pitfalls
   - Performance issues
   - Security concerns

7. **C4 (flake8-comprehensions)** - Comprehension improvements
   - More efficient comprehensions
   - Unnecessary comprehensions

8. **SIM (flake8-simplify)** - Code simplification
   - Complex conditionals
   - Redundant operations
   - Better alternatives

9. **TCH (flake8-type-checking)** - Type checking imports
   - Runtime vs type-checking imports
   - Import optimization

10. **Q (flake8-quotes)** - Quote consistency
    - Double quotes preferred
    - Consistent usage

### Disabled Rules

- **E501** - Line too long (formatter handles this)
- **B008** - Function calls in defaults (needed for FastAPI/SQLAlchemy)
- **B904** - Raise exceptions without `from` (sometimes intentional)

## CI/CD Integration

Ruff is integrated into the CI/CD pipeline via GitHub Actions. See `docs/CI_CD_SETUP.md` for details.

### GitHub Actions

The workflow runs:
1. **Linting**: `ruff check src tests`
2. **Format Check**: `ruff format --check src tests`

Both must pass for PR approval.

### Pre-commit Hooks

Ruff runs automatically before each commit:
1. **Linter** - Checks and auto-fixes issues
2. **Formatter** - Formats code automatically

Configuration in `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
        args: [ --fix ]
      - id: ruff-format
```

## Common Commands

### Daily Development

```bash
# Before committing (runs automatically via pre-commit)
poetry run ruff check . --fix
poetry run ruff format .

# Manual pre-commit run
poetry run pre-commit run --all-files
```

### CI/CD Simulation

```bash
# Simulate CI checks locally
poetry run ruff check src tests
poetry run ruff format --check src tests
poetry run pytest -v
```

### Specific Checks

```bash
# Check only import sorting
poetry run ruff check . --select I

# Check only naming conventions
poetry run ruff check . --select N

# Check only bugs
poetry run ruff check . --select B
```

## Best Practices

### For Developers

1. **Let pre-commit hooks run** - They auto-fix most issues
2. **Review auto-fixes** - Understand what changed
3. **Run checks before pushing** - Catch issues early
4. **Keep ruff updated** - New rules and fixes regularly

### Writing Clean Code

1. **Follow naming conventions**:
   ```python
   # Good
   class UserModel:
       pass

   def get_user_data():
       pass

   API_KEY = "secret"

   # Bad
   class user_model:  # Should be UserModel
       pass

   def GetUserData():  # Should be get_user_data
       pass

   api_key = "secret"  # Should be API_KEY (constant)
   ```

2. **Use modern syntax**:
   ```python
   # Good (Python 3.10+)
   def greet(name: str | None = None) -> str:
       return f"Hello, {name or 'World'}!"

   # Old style (ruff will suggest upgrade)
   from typing import Optional
   def greet(name: Optional[str] = None) -> str:
       return f"Hello, {name or 'World'}!"
   ```

3. **Simplify code**:
   ```python
   # Good
   return bool(value)

   # Bad (ruff will suggest simplification)
   if value:
       return True
   else:
       return False
   ```

## Troubleshooting

### Issue: Ruff not found

```bash
# Ensure ruff is installed
poetry install

# Verify installation
poetry run ruff --version
```

### Issue: Pre-commit hooks not running

```bash
# Reinstall hooks
poetry run pre-commit install

# Test hooks manually
poetry run pre-commit run --all-files
```

### Issue: Formatting conflicts

If ruff format changes are reverted:
1. Check editor settings (disable other formatters)
2. Ensure editor doesn't run conflicting formatters
3. Let ruff be the single source of truth

### Issue: Too many errors

```bash
# Fix auto-fixable issues first
poetry run ruff check . --fix

# Then review remaining issues
poetry run ruff check .

# Focus on one category at a time
poetry run ruff check . --select F  # Just Pyflakes
poetry run ruff check . --select I  # Just imports
```

### Ignoring Specific Lines

If ruff flags a false positive or unavoidable issue:

```python
# Single line
result = eval(user_input)  # noqa: S307

# Multiple rules
x = 1; y = 2  # noqa: E702, E701

# Entire file (use sparingly)
# ruff: noqa

# Entire block
# ruff: noqa: E501
long_line_1 = "very long string..."
long_line_2 = "very long string..."
# ruff: noqa: E501
```

## Migration from Other Tools

### From Pylint

Ruff covers most pylint functionality:
- ✅ Faster (10-100x)
- ✅ Better auto-fix
- ✅ Modern rule sets
- ✅ Simpler configuration

Key differences:
- Ruff doesn't calculate complexity scores
- Ruff doesn't have custom plugins
- Ruff focuses on practical, actionable rules

### From Black

Ruff format is Black-compatible:
- ✅ Same formatting output
- ✅ Faster formatting
- ✅ Integrated with linting
- ✅ Single tool instead of two

### From Flake8 + isort

Ruff replaces both:
- ✅ All Flake8 rules included
- ✅ isort functionality built-in
- ✅ Faster execution
- ✅ Unified configuration

## Monitoring

### Key Metrics

1. **Error Count**: Should be 0
2. **Warning Count**: Track trends
3. **Auto-fixed Issues**: Monitor what's being fixed
4. **Formatting Changes**: Should decrease over time

### Health Check

```bash
# Quick health check
poetry run ruff check . --statistics

# Detailed report
poetry run ruff check . --output-format=json > ruff-report.json
```

## Updating Ruff

### Update Pre-commit Hooks

```bash
# Update to latest versions
poetry run pre-commit autoupdate

# Test updated hooks
poetry run pre-commit run --all-files
```

### Update Ruff Package

```bash
# Update ruff
poetry update ruff

# Verify new version
poetry run ruff --version
```

## Additional Resources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Ruff Rules](https://docs.astral.sh/ruff/rules/)
- [Ruff Settings](https://docs.astral.sh/ruff/settings/)
- [Ruff FAQ](https://docs.astral.sh/ruff/faq/)
- [CI/CD Setup Documentation](./CI_CD_SETUP.md)

## Rule Reference

For a complete list of rules and their codes, visit:
https://docs.astral.sh/ruff/rules/

Quick rule lookup:
```bash
# Show all available rules
poetry run ruff linter

# Show rules for specific category
poetry run ruff linter | grep "E[0-9]"  # pycodestyle errors
poetry run ruff linter | grep "F[0-9]"  # Pyflakes
poetry run ruff linter | grep "B[0-9]"  # flake8-bugbear
