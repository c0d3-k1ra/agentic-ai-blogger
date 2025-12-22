#!/bin/bash
set -e

echo "🚀 Starting PostgreSQL with Docker..."

# Check if postgres-test container exists and is running
if docker ps -a --format '{{.Names}}' | grep -q "^postgres-test$"; then
    if ! docker ps --format '{{.Names}}' | grep -q "^postgres-test$"; then
        echo "📦 Starting existing PostgreSQL container..."
        docker start postgres-test
    else
        echo "✅ PostgreSQL container already running"
    fi
else
    echo "📦 Creating new PostgreSQL container..."
    docker run -d \
        --name postgres-test \
        -e POSTGRES_USER=test \
        -e POSTGRES_PASSWORD=test \
        -e POSTGRES_DB=testdb \
        -p 5432:5432 \
        postgres:17

    echo "⏳ Waiting for PostgreSQL to be ready..."
    sleep 5
fi

# Wait for PostgreSQL to accept connections
echo "🔍 Checking PostgreSQL health..."
max_attempts=30
attempt=0

while ! docker exec postgres-test pg_isready -U test > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo "❌ PostgreSQL failed to start after $max_attempts attempts"
        exit 1
    fi
    echo "⏳ Waiting for PostgreSQL... (attempt $attempt/$max_attempts)"
    sleep 1
done

echo "✅ PostgreSQL is ready"
echo "🧪 Running integration tests..."

# Run integration tests with explicit path (no coverage)
poetry run pytest integration_tests/ --no-cov -v "$@"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "✨ Integration tests complete!"
else
    echo "❌ Integration tests failed"
fi

exit $exit_code
