# Tech Article Generator

A minimal, well-structured Python project for generating technical articles with robust database integration and structured logging.

## Features

- 🗄️ **PostgreSQL Integration** - SQLAlchemy-based database layer with connection pooling
- 🔄 **Retry Mechanism** - Automatic retry logic for transient database errors
- 📝 **Structured Logging** - JSON and standard format logging with configurable levels
- ⚙️ **Configuration Management** - Pydantic-based settings with environment variable support
- ✅ **Testing Ready** - Pytest configuration with comprehensive test coverage
- 🔍 **Code Quality** - Ruff linter and formatter with comprehensive rule coverage
- 🚀 **CI/CD Ready** - GitHub Actions workflow and pre-commit hooks configured

## Project Structure

```txt
tech-article-generator/
├── src/
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db.py           # Database connection layer
│   │   └── models.py       # SQLAlchemy models
│   └── utils/
│       ├── __init__.py
│       ├── config.py       # Configuration management
│       └── logging_config.py  # Logging setup
├── tests/
│   ├── test_config.py
│   ├── test_logging.py
│   └── test_database/
│       ├── test_connection.py
│       └── test_models.py
├── docs/
│   ├── DATABASE_SETUP.md   # Database setup guide
│   ├── RUFF_SETUP.md      # Code quality and linting guide
│   └── CI_CD_SETUP.md     # CI/CD configuration guide
├── .github/
│   └── workflows/
│       └── ci.yml         # GitHub Actions CI/CD
├── pyproject.toml          # Poetry & Ruff configuration
├── requirements.txt        # Pip dependencies
├── .pre-commit-config.yaml # Pre-commit hooks config
├── .env.example           # Environment template
└── README.md              # This file
```

## Installation

### Using pip

```bash
# Clone the repository
git clone <repository-url>
cd tech-article-generator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install project in editable mode
pip install -e .
```

### Using Poetry

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

## Configuration

1. **Copy environment template:**

   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your settings:**

   ```env
   # Application
   APP_NAME=tech-article-generator
   ENVIRONMENT=development
   DEBUG=true

   # Database
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=tech_articles
   DB_USER=your_user
   DB_PASSWORD=your_password

   # Database Connection Pool
   DB_POOL_SIZE=5
   DB_MAX_OVERFLOW=10
   DB_POOL_TIMEOUT=30
   DB_MAX_RETRIES=3
   DB_RETRY_DELAY=1.0

   # Logging
   LOG_LEVEL=INFO
   ```

## Usage

### Database Operations

```python
from src.database.db import init_db, get_session, health_check

# Initialize database
init_db()

# Check connectivity
if health_check():
    print("Database is connected!")

# Use database session
with get_session() as session:
    # Your database operations here
    result = session.execute(...)
```

### Logging

```python
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

logger.info("Application started")
logger.error("An error occurred", extra_fields={"user_id": 123})
```

### Configurations

```python
from src.utils.config import get_settings

settings = get_settings()
print(f"App: {settings.APP_NAME}")
print(f"DB URL: {settings.get_database_url()}")
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run with verbose output
pytest -v
```

## Code Quality

This project uses **Ruff** - an extremely fast Python linter and formatter written in Rust.

```bash
# Check code quality
poetry run ruff check .

# Auto-fix issues
poetry run ruff check . --fix

# Format code
poetry run ruff format .

# Run all checks (pre-commit simulation)
poetry run pre-commit run --all-files
```

For more details on code quality standards, see the [Ruff Configuration Guide](docs/RUFF_SETUP.md) and [CI/CD Setup Guide](docs/CI_CD_SETUP.md).

## Documentation

- 📚 **[Database Setup Guide](docs/DATABASE_SETUP.md)** - Comprehensive guide for database configuration, connection management, and best practices
- 🔍 **[Ruff Configuration Guide](docs/RUFF_SETUP.md)** - Linting and formatting standards, rules, and best practices
- 🚀 **[CI/CD Setup Guide](docs/CI_CD_SETUP.md)** - GitHub Actions workflow and pre-commit hooks configuration

## Development

### Adding New Features

1. Create feature branch
2. Write tests first (TDD approach)
3. Implement feature
4. Ensure ruff checks pass (pre-commit hooks handle this automatically)
5. Run tests: `pytest`
6. Submit pull request

### Pre-commit Checklist

Pre-commit hooks automatically handle most of these:

- [ ] All tests pass (`poetry run pytest`)
- [ ] Ruff checks pass (`poetry run ruff check .`)
- [ ] Code is formatted (`poetry run ruff format .`)
- [ ] Documentation updated
- [ ] Environment variables documented in `.env.example`

## Requirements

- Python 3.8+
- PostgreSQL 12+
- pip or Poetry

## Dependencies

**Core:**

- SQLAlchemy 2.0+ - Database ORM
- psycopg2-binary 2.9+ - PostgreSQL adapter
- pydantic-settings 2.0+ - Configuration management

**Development:**

- pytest 7.4+ - Testing framework
- ruff 0.8+ - Fast Python linter and formatter
- pre-commit 3.8+ - Git hook framework

## License

[Your License Here]

## Contributing

Contributions are welcome! Please ensure:

1. Code passes all tests
2. Ruff checks pass (pre-commit hooks will run automatically)
3. Documentation is updated
4. Follow existing code style (enforced by ruff formatter)

## Support

For issues and questions:

- Create an issue in the repository
- Check the [documentation](docs/)
- Review existing issues

---

**Current Status:** ✅ Production Ready

- Database: Configured with retry logic
- Logging: Structured logging enabled
- Testing: 135/135 tests passing
- Code Quality: All ruff checks passing
- CI/CD: GitHub Actions and pre-commit hooks configured
