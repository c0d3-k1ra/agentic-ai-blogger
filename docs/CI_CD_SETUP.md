# CI/CD Setup Documentation

This document describes the CI/CD setup for the tech-article-generator project.

## Overview

The project uses two complementary approaches for automated code quality:

1. **Pre-commit Hooks** - Local checks before committing code
2. **GitHub Actions** - Remote CI/CD pipeline on push/PR

## Pre-commit Hooks

### What are Pre-commit Hooks?

Pre-commit hooks automatically run checks on your code before each git commit, catching issues early in the development process.

### Installed Hooks

1. **Ruff Linter** - Fast Python linting with auto-fix
2. **Ruff Format** - Code formatting
3. **Trailing Whitespace** - Removes trailing spaces
4. **End of File Fixer** - Ensures files end with newline
5. **YAML Check** - Validates YAML syntax
6. **Large Files Check** - Prevents committing large files (>1MB)
7. **JSON Check** - Validates JSON syntax
8. **TOML Check** - Validates TOML syntax
9. **Merge Conflict Check** - Detects merge conflict markers
10. **Private Key Detection** - Prevents committing private keys

### Setup

Pre-commit hooks are already installed. They will run automatically on every commit.

To manually run all hooks on all files:
```bash
poetry run pre-commit run --all-files
```

To update hook versions:
```bash
poetry run pre-commit autoupdate
```

To bypass hooks temporarily (not recommended):
```bash
git commit --no-verify
```

### Configuration

Pre-commit hooks are configured in `.pre-commit-config.yaml`. Key settings:

- **Ruff** runs with `--fix` to auto-correct issues
- **Large files** are limited to 1000KB
- Hooks run on all relevant file types

## GitHub Actions CI/CD

### Workflow Overview

The CI/CD pipeline runs on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

### Jobs

#### 1. Test Job

Runs tests across multiple Python versions to ensure compatibility.

**Python Versions Tested:**
- Python 3.8
- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12

**Steps:**
1. Checkout code
2. Set up Python environment
3. Install Poetry
4. Cache dependencies for faster runs
5. Install project dependencies
6. Run ruff linting checks
7. Run pytest test suite

**Environment Variables:**
- `APP_NAME=test-app`
- `ENVIRONMENT=development`
- `LOG_LEVEL=INFO`

#### 2. Ruff Format Check Job

Verifies code formatting consistency.

**Steps:**
1. Checkout code
2. Set up Python 3.11
3. Install Poetry and dependencies
4. Check code formatting with ruff

### Viewing Results

1. Navigate to your repository on GitHub
2. Click the "Actions" tab
3. Select a workflow run to see detailed results
4. Failed jobs will show which step failed and why

### Caching

The workflow uses GitHub Actions cache to:
- Speed up subsequent runs
- Reduce dependency installation time
- Cache is keyed by Python version and `poetry.lock` hash

### Workflow File

Location: `.github/workflows/ci.yml`

## Best Practices

### For Developers

1. **Run tests locally** before pushing:
   ```bash
   poetry run pytest -v
   ```

2. **Let pre-commit hooks run** - they catch issues early

3. **Review CI failures** - don't ignore failed checks

4. **Keep dependencies updated** - regularly update `poetry.lock`

### For Pull Requests

1. **Ensure CI passes** before requesting review
2. **Fix linting issues** flagged by ruff
3. **Address test failures** promptly
4. **Keep commits clean** - pre-commit hooks help with this

## Troubleshooting

### Pre-commit Hook Failures

**Issue:** Hook fails on commit
**Solution:**
1. Review the error message
2. Fix the reported issue
3. Stage the fixed files: `git add <file>`
4. Commit again

**Issue:** Need to commit despite hook failure (emergency only)
**Solution:** `git commit --no-verify`

### GitHub Actions Failures

**Issue:** Tests fail in CI but pass locally
**Solution:**
1. Check Python version differences
2. Verify environment variables are set correctly
3. Look for missing dependencies in `pyproject.toml`
4. Check for filesystem/OS-specific issues

**Issue:** Workflow doesn't run
**Solution:**
1. Ensure you're pushing to `main` or `develop` branch
2. Check workflow file syntax in `.github/workflows/ci.yml`
3. Verify GitHub Actions are enabled for the repository

## Adding New Checks

### Adding a Pre-commit Hook

Edit `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/your/hook
    rev: v1.0.0
    hooks:
      - id: hook-name
        args: ['--arg1', 'value1']
```

Then update hooks:
```bash
poetry run pre-commit install
poetry run pre-commit run --all-files
```

### Adding a CI Job

Edit `.github/workflows/ci.yml`:

```yaml
jobs:
  new-job:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Your step
        run: your-command
```

## Configuration Files

- `.pre-commit-config.yaml` - Pre-commit hook configuration
- `.github/workflows/ci.yml` - GitHub Actions workflow
- `pyproject.toml` - Ruff linter configuration (under `[tool.ruff]`)

## Monitoring

### Key Metrics to Watch

1. **Test Pass Rate** - Should be 100%
2. **Build Time** - Monitor for increases (may indicate issues)
3. **Coverage** - Track test coverage trends
4. **Linting Errors** - Should decrease over time

### GitHub Badges

You can add status badges to your README:

```markdown
![CI](https://github.com/your-username/tech-article-generator/workflows/CI/badge.svg)
```

## Additional Resources

- [Pre-commit Documentation](https://pre-commit.com)
- [GitHub Actions Documentation](https://docs.github.com/actions)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Poetry Documentation](https://python-poetry.org/docs/)
