# Database Connection Layer

A production-ready PostgreSQL database connection layer built with SQLAlchemy.

## Features

- **Connection Pooling**: Efficient connection management with configurable pool sizes
- **Automatic Retry Logic**: Handles transient database errors with exponential backoff
- **Transaction Management**: Automatic commit/rollback for database sessions
- **Health Checks**: Built-in database connectivity verification
- **Configurable Settings**: Environment-based configuration for all database parameters

## Quick Start

### 1. Install Dependencies

```bash
pip install -e .
```

### 2. Configure Database

Set your database URL in the environment:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/dbname"
```

Or add it to your `.env` file:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

### 3. Initialize Database

```python
from src.database.db import init_db, get_session

# Initialize the database connection
init_db()

# Use a database session
with get_session() as session:
    result = session.execute("SELECT 1")
    print(result.fetchone())
```

## Configuration Options

All database configuration is done through environment variables:

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `DATABASE_URL` | **Required** | PostgreSQL connection string |
| `DB_POOL_SIZE` | 5 | Number of connections to maintain in the pool |
| `DB_MAX_OVERFLOW` | 10 | Max connections beyond pool_size |
| `DB_POOL_TIMEOUT` | 30 | Seconds to wait for available connection |
| `DB_MAX_RETRIES` | 3 | Max retry attempts for transient errors |
| `DB_RETRY_DELAY` | 1.0 | Initial delay between retries (seconds) |

## API Reference

### `init_db()`

Initialize the database engine and session factory.

**Must be called before using any other database functions.**

```python
from src.database.db import init_db

init_db()
```

**Raises:**

- `DatabaseConnectionError`: If DATABASE_URL is not configured
- `DatabaseError`: If engine creation fails

### `get_session()`

Context manager for database sessions with automatic transaction management.

```python
from src.database.db import get_session

with get_session() as session:
    # Your database operations
    user = session.query(User).filter_by(id=1).first()
    # Automatically commits on success
```

**Features:**

- Automatically commits on successful execution
- Automatically rolls back on errors
- Always closes the session
- Retries on transient errors (connection failures, deadlocks, etc.)

**Raises:**

- `DatabaseError`: If session factory is not initialized
- `DatabaseRetryError`: If all retry attempts fail

### `get_engine()`

Get the SQLAlchemy engine instance.

```python
from src.database.db import get_engine

engine = get_engine()
# Use engine for raw SQL or migrations
```

**Returns:** SQLAlchemy Engine instance

**Raises:**

- `DatabaseError`: If engine is not initialized

### `health_check()`

Check database connectivity.

```python
from src.database.db import health_check

if health_check():
    print("Database is healthy")
```

**Returns:** `True` if database is accessible

**Raises:**

- `DatabaseError`: If engine is not initialized
- `DatabaseRetryError`: If all retry attempts fail

### `close_db()`

Close database connections and cleanup resources.

```python
from src.database.db import close_db

close_db()
```

Useful for cleanup in tests or application shutdown.

## Error Handling

### Exception Hierarchy

```txt
DatabaseError (base exception)
├── DatabaseConnectionError (connection setup failures)
└── DatabaseRetryError (retry exhaustion)
```

### Transient Error Retry

The connection layer automatically retries on transient errors:

- Connection refused/reset/timeout
- Deadlocks
- Connection pool exhaustion
- Server closed connection

**Retry Strategy:**

- Exponential backoff: 1s, 2s, 4s, etc.
- Configurable max retries (default: 3)
- Only retries transient errors

Example:

```python
from src.database.db import get_session, DatabaseRetryError

try:
    with get_session() as session:
        # Database operation
        pass
except DatabaseRetryError as e:
    # All retry attempts failed
    print(f"Failed after retries: {e}")
```

## Connection Pooling

The database layer uses SQLAlchemy's connection pooling:

- **pool_size**: Minimum connections maintained (default: 5)
- **max_overflow**: Additional connections when needed (default: 10)
- **pool_timeout**: Wait time for available connection (default: 30s)
- **pool_pre_ping**: Verifies connections before use (enabled)

Total max connections = pool_size + max_overflow = 15 (default)

## Best Practices

### 1. Always Use Context Managers

```python
# Good ✓
with get_session() as session:
    result = session.query(User).all()

# Bad ✗
session = Session()  # Manual session management
```

### 2. Initialize Once at Startup

```python
# In your application startup
from src.database.db import init_db

def startup():
    init_db()
    # ... rest of startup
```

### 3. Handle Exceptions Appropriately

```python
from src.database.db import get_session, DatabaseError

try:
    with get_session() as session:
        # Operations
        pass
except DatabaseError as e:
    # Log and handle database errors
    logger.error(f"Database error: {e}")
    raise
```

### 4. Use Health Checks

```python
from src.database.db import health_check

# In health check endpoint
@app.get("/health")
def health():
    if not health_check():
        return {"status": "unhealthy"}, 503
    return {"status": "healthy"}
```

## Testing

The database layer includes comprehensive tests:

```bash
# Run database tests
pytest tests/test_database/

# Run all tests
pytest
```

### Test Coverage

- Database initialization
- Session management (commit/rollback)
- Retry logic and exponential backoff
- Health checks
- Error handling
- Connection cleanup

## Example Usage

### Basic Query

```python
from src.database.db import init_db, get_session
from sqlalchemy import text

init_db()

with get_session() as session:
    result = session.execute(text("SELECT * FROM users"))
    users = result.fetchall()
```

### With SQLAlchemy ORM

```python
from src.database.db import init_db, get_session
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)

init_db()

with get_session() as session:
    user = session.query(User).filter_by(id=1).first()
    print(user.name)
```

### Handling Transient Errors

```python
from src.database.db import get_session, DatabaseRetryError
import logging

logger = logging.getLogger(__name__)

try:
    with get_session() as session:
        # This will automatically retry on connection errors
        result = session.execute(text("SELECT 1"))
except DatabaseRetryError as e:
    logger.error(f"Database operation failed after retries: {e}")
    # Handle failure (e.g., return error to user)
```

## Database Migrations with Alembic

### Overview

Alembic is our database migration tool that tracks and applies schema changes over time. It works alongside SQLAlchemy to:

- Version control your database schema
- Apply changes consistently across environments
- Provide rollback capability for schema changes
- Generate migrations automatically from model changes

### Quick Start with Migrations

#### Check Current Migration State

```bash
poetry run alembic current
```

Shows the current revision your database is at.

#### Apply All Pending Migrations

```bash
poetry run alembic upgrade head
```

Applies all migrations up to the latest version.

#### Rollback One Migration

```bash
poetry run alembic downgrade -1
```

Reverts the most recent migration.

### Common Migration Commands

| Command | Description |
| --------- | ------------- |
| `alembic current` | Show current migration revision |
| `alembic upgrade head` | Apply all pending migrations |
| `alembic downgrade -1` | Rollback one migration |
| `alembic downgrade base` | Rollback all migrations |
| `alembic history` | Show migration history |
| `alembic revision --autogenerate -m "msg"` | Create new migration |

### Creating New Migrations

When you modify SQLAlchemy models in `src/database/models.py`, create a migration:

```bash
# Generate migration from model changes
poetry run alembic revision --autogenerate -m "add user email column"
```

This will:
1. Compare your models to the current database schema
2. Generate a new migration file in `migrations/versions/`
3. Include both `upgrade()` and `downgrade()` functions

**Always review auto-generated migrations before applying them!**

### Migration File Structure

Each migration file contains:

```python
def upgrade() -> None:
    """Upgrade schema - apply changes."""
    # SQL operations to move forward
    op.create_table(...)
    op.add_column(...)

def downgrade() -> None:
    """Downgrade schema - revert changes."""
    # SQL operations to rollback
    op.drop_column(...)
    op.drop_table(...)
```

### Migration Workflow

#### 1. Development Workflow

```bash
# 1. Modify models in src/database/models.py
# 2. Generate migration
poetry run alembic revision --autogenerate -m "add new table"

# 3. Review generated migration file
cat migrations/versions/XXXXX_add_new_table.py

# 4. Test upgrade
poetry run alembic upgrade head

# 5. Test downgrade
poetry run alembic downgrade -1

# 6. Test upgrade again (round-trip)
poetry run alembic upgrade head

# 7. Commit migration file to git
git add migrations/versions/XXXXX_add_new_table.py
git commit -m "Add migration for new table"
```

#### 2. Production Deployment

```bash
# On production server after deploying new code
poetry run alembic upgrade head
```

### Configuration

#### Database Connection

Alembic reads the database URL from the `DATABASE_URL` environment variable:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/dbname"
```

Or add to `.env` file:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

#### Configuration Files

- `alembic.ini` - Main Alembic configuration
- `migrations/env.py` - Environment setup (loads .env, imports models)
- `migrations/versions/` - Directory containing migration files

### Best Practices

#### ✅ DO

- **Always test both upgrade AND downgrade** before committing
- **Review auto-generated migrations** - Alembic might miss some changes
- **Keep migrations focused** - One logical change per migration
- **Test on production-like data** before deploying
- **Commit migrations with related code** in the same PR
- **Keep downgrade functions complete** - Always be able to rollback

#### ❌ DON'T

- **Never modify committed migrations** - Create a new migration instead
- **Don't skip migrations** - Always apply migrations in order
- **Don't mix data and schema migrations** - Keep them separate
- **Don't use raw SQL without necessity** - Prefer Alembic operations
- **Don't forget to test downgrade** - It's there for a reason

### Common Operations

#### Add a Column

```python
def upgrade():
    op.add_column('users', sa.Column('email', sa.String(255), nullable=True))

def downgrade():
    op.drop_column('users', 'email')
```

#### Create a Table

```python
def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False)
    )

def downgrade():
    op.drop_table('users')
```

#### Add an Index

```python
def upgrade():
    op.create_index('ix_users_email', 'users', ['email'])

def downgrade():
    op.drop_index('ix_users_email', table_name='users')
```

### Handling ENUM Types (PostgreSQL)

PostgreSQL ENUMs require special handling:

```python
def upgrade():
    # Create ENUM type
    status_enum = postgresql.ENUM('draft', 'published', name='status_enum')
    status_enum.create(op.get_bind())

    # Use in column
    op.add_column('articles',
        sa.Column('status', status_enum, server_default='draft'))

def downgrade():
    op.drop_column('articles', 'status')

    # Drop ENUM type
    op.execute('DROP TYPE IF EXISTS status_enum')
```

### Migration Branches and Conflicts

If multiple developers create migrations simultaneously:

```bash
# Check for multiple heads
poetry run alembic heads

# Merge branches
poetry run alembic merge -m "merge migrations" head1 head2
```

### Troubleshooting Migrations

#### Migration is Stuck

```bash
# Force set revision (use with caution!)
poetry run alembic stamp head
```

#### Migration Failed Mid-way

```bash
# Manually fix database state, then:
poetry run alembic stamp <revision_id>
```

#### Need to Skip a Bad Migration

```bash
# Downgrade before the bad migration
poetry run alembic downgrade <previous_revision>

# Fix the migration file or create a new one
poetry run alembic revision --autogenerate -m "fix schema"

# Apply new migration
poetry run alembic upgrade head
```

## Troubleshooting

### "Database not initialized" Error

**Problem:** Calling database functions before `init_db()`

**Solution:**

```python
from src.database.db import init_db
init_db()  # Call this first
```

### Connection Pool Exhausted

**Problem:** Too many concurrent connections

**Solutions:**

1. Increase pool size: `DB_POOL_SIZE=10`
2. Increase max overflow: `DB_MAX_OVERFLOW=20`
3. Ensure sessions are properly closed (use context managers)

### Retry Exhaustion

**Problem:** `DatabaseRetryError` after all retries

**Possible Causes:**

1. Database is down
2. Network issues
3. Incorrect credentials
4. Database overloaded

**Check:**

- Database server status
- Network connectivity
- Connection string validity
- Database logs

## Architecture

```txt
┌─────────────────┐
│  Application    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  get_session()  │  ← Context manager with retry logic
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Session Factory │  ← Created by init_db()
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  SQLAlchemy     │  ← Connection pooling
│     Engine      │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   PostgreSQL    │
└─────────────────┘
```

## License

Part of the tech-article-generator project.
