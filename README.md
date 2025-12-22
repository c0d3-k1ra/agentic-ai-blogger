# Tech Article Generator

A minimal, well-structured Python project for generating technical articles with robust database integration and structured logging.

## Features

- 🗄️ **PostgreSQL Integration** - SQLAlchemy-based database layer with connection pooling
- 🔄 **Retry Mechanism** - Automatic retry logic for transient database errors
- 📝 **Structured Logging** - JSON and standard format logging with configurable levels
- ⚙️ **Configuration Management** - Pydantic-based settings with environment variable support
- ✅ **Testing Ready** - Pytest configuration with comprehensive test coverage
- 🔍 **Code Quality** - Pylint configured with 10.00/10 score (minimum 9.0/10 enforced)

## Project Structure

```
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
│   └── PYLINT_SETUP.md     # Code quality guide
├── pyproject.toml          # Poetry configuration
├── requirements.txt        # Pip dependencies
├── .pylintrc              # Pylint configuration
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

### Configuration

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

This project maintains a **10.00/10 pylint score** with a minimum requirement of **9.0/10**.

```bash
# Check code quality
pylint src/

# Expected output:
# Your code has been rated at 10.00/10
```

For more details on code quality standards, see the [Pylint Configuration Guide](docs/PYLINT_SETUP.md).

## Documentation

- 📚 **[Database Setup Guide](docs/DATABASE_SETUP.md)** - Comprehensive guide for database configuration, connection management, and best practices
- 🔍 **[Pylint Configuration Guide](docs/PYLINT_SETUP.md)** - Code quality standards, CI/CD integration, and troubleshooting

## Development

### Adding New Features

1. Create feature branch
2. Write tests first (TDD approach)
3. Implement feature
4. Ensure pylint score ≥ 9.0
5. Run tests: `pytest`
6. Submit pull request

### Pre-commit Checklist

- [ ] All tests pass (`pytest`)
- [ ] Code quality check passes (`pylint src/`)
- [ ] No errors or warnings
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
- pylint 3.0+ - Code quality checker

## License

[Your License Here]

## Contributing

Contributions are welcome! Please ensure:
1. Code passes all tests
2. Pylint score ≥ 9.0
3. Documentation is updated
4. Follow existing code style

## Support

For issues and questions:
- Create an issue in the repository
- Check the [documentation](docs/)
- Review existing issues

---

**Current Status:** ✅ Production Ready
- Database: Configured with retry logic
- Logging: Structured logging enabled
- Testing: Comprehensive test coverage
- Code Quality: 10.00/10 pylint score
