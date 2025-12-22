# Pylint Configuration

This project uses pylint for code quality enforcement with strict standards.

## Configuration Summary

- **Minimum Score:** 9.5/10 (strict)
- **Failure Policy:** Errors only (warnings allowed)
- **Current Score:** 10.00/10 ✨
- **Scope:** Only `src/` directory (tests excluded)

## Configuration File

The `.pylintrc` file contains:

```ini
[MAIN]
fail-under=9.5              # Minimum score required (strict)
fail-on=E                   # Fail only on errors (E), not warnings (W)
ignore=tests,example_logging.py,.env,pytest.ini,poetry.lock

[MESSAGES CONTROL]
disable=
    too-few-public-methods,
    global-statement,
    broad-exception-caught,
    unsubscriptable-object,
    no-member,
    duplicate-code
```

## Usage

### Basic Check

```bash
# Run pylint on entire project (only checks src/ directory)
pylint .

# Expected output:
# Your code has been rated at 10.00/10
# Exit code: 0 (success)
```

### With Detailed Reports

```bash
pylint . --reports=y
```

### Check Specific Files

```bash
pylint src/database/db.py
pylint src/utils/config.py
```

### What Gets Checked

**Included:** ✅ `src/` directory only  
**Excluded:** ❌ `tests/`, `example_logging.py`, config files

## Exit Codes

- **0** - Success (score >= 9.5 and no errors)
- **1** - Fatal message issued
- **2** - Error message issued (will fail CI/CD)
- **4** - Warning message issued (won't fail CI/CD)
- **8** - Refactor message issued
- **16** - Convention message issued
- **32** - Usage error (score < 9.5)

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run pylint
        run: |
          pylint src/
          # Fails if score < 9.0 or any errors found
```

### GitLab CI Example

```yaml
lint:
  stage: test
  script:
    - pip install -r requirements.txt
    - pylint src/
  only:
    - merge_requests
    - main
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pylint
        name: pylint
        entry: pylint
        language: system
        types: [python]
        args: ["--fail-under=9.0", "--fail-on=E"]
```

## Disabled Checks

The following checks are disabled for valid project reasons:

- `too-few-public-methods` - Models and exceptions are fine with few methods
- `global-statement` - Acceptable for singleton pattern
- `broad-exception-caught` - Sometimes necessary for retry logic
- `unsubscriptable-object` - False positive with SQLAlchemy/Pydantic
- `no-member` - False positive with Pydantic SecretStr

## Best Practices

1. **Before Committing:** Always run `pylint src/` locally
2. **Target Score:** Aim for 10.00/10 in new code
3. **Error-Free:** Never commit code with errors
4. **Warnings:** Address warnings when reasonable, but they won't block merges

## Troubleshooting

### Score Below 9.0

```bash
# Get detailed report
pylint src/ --reports=y

# Focus on specific issues
pylint src/ --disable=W,C,R  # Only show errors
```

### False Positives

If pylint reports false positives, add inline comments:

```python
# pylint: disable=specific-warning-name
problematic_code_here()
# pylint: enable=specific-warning-name
```

Or add to `.pylintrc` if project-wide.

## Maintenance

To update the minimum score requirement, edit `.pylintrc`:

```ini
[MAIN]
fail-under=9.5  # Increase strictness
```

To change failure policy:

```ini
[MAIN]
fail-on=E,F  # Fail on errors and fatal messages only
