"""Tests for database connection layer."""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy import exc

from src.database.db import (DatabaseConnectionError, DatabaseError,
                             DatabaseRetryError, _is_transient_error, close_db,
                             get_engine, get_session, health_check, init_db,
                             retry_on_transient_error)
from src.utils.config import reset_settings


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables before each test."""
    os.environ["APP_NAME"] = "test-app"
    os.environ["ENVIRONMENT"] = "development"
    os.environ["LOG_LEVEL"] = "INFO"
    os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/testdb"
    os.environ["DB_MAX_RETRIES"] = "3"
    os.environ["DB_RETRY_DELAY"] = "0.1"  # Fast retries for tests
    
    # Reset settings and database state before each test
    reset_settings()
    close_db()
    
    yield
    
    # Cleanup after test
    close_db()
    reset_settings()


class TestDatabaseInitialization:
    """Tests for database initialization."""
    
    def test_init_db_creates_engine_and_session_factory(self):
        """Test that init_db creates engine and session factory."""
        with patch("src.database.db.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine
            
            init_db()
            
            # Verify engine was created with correct parameters
            mock_create_engine.assert_called_once()
            args, kwargs = mock_create_engine.call_args
            
            assert args[0] == "postgresql://test:test@localhost:5432/testdb"
            assert kwargs["pool_size"] == 5
            assert kwargs["max_overflow"] == 10
            assert kwargs["pool_timeout"] == 30
            assert kwargs["pool_pre_ping"] is True
    
    def test_init_db_raises_error_without_database_url(self, monkeypatch, tmp_path):
        """Test that init_db raises error when DATABASE_URL is not set."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("APP_NAME", "test-app")
        monkeypatch.setenv("ENVIRONMENT", "development")
        # Change to tmp directory to avoid loading .env
        monkeypatch.chdir(tmp_path)
        reset_settings()
        
        with pytest.raises(DatabaseConnectionError) as exc_info:
            init_db()
        
        assert "DATABASE_URL is not configured" in str(exc_info.value)
    
    def test_init_db_raises_error_on_connection_failure(self):
        """Test that init_db raises DatabaseError on connection failure."""
        with patch("src.database.db.create_engine") as mock_create_engine:
            mock_create_engine.side_effect = Exception("Connection failed")
            
            with pytest.raises(DatabaseError) as exc_info:
                init_db()
            
            assert "Database initialization failed" in str(exc_info.value)
    
    def test_get_engine_raises_error_if_not_initialized(self):
        """Test that get_engine raises error if init_db not called."""
        with pytest.raises(DatabaseError) as exc_info:
            get_engine()
        
        assert "not initialized" in str(exc_info.value)
    
    def test_get_engine_returns_engine_after_init(self):
        """Test that get_engine returns engine after initialization."""
        with patch("src.database.db.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine
            
            init_db()
            engine = get_engine()
            
            assert engine is mock_engine


class TestSessionManagement:
    """Tests for database session management."""
    
    def test_get_session_raises_error_if_not_initialized(self):
        """Test that get_session raises error if init_db not called."""
        with pytest.raises(DatabaseError) as exc_info:
            with get_session():
                pass
        
        assert "not initialized" in str(exc_info.value)
    
    def test_get_session_commits_on_success(self):
        """Test that session commits on successful execution."""
        with patch("src.database.db.create_engine"):
            init_db()
            
            with patch("src.database.db._session_factory") as mock_factory:
                mock_session = MagicMock()
                mock_factory.return_value = mock_session
                
                with get_session() as session:
                    assert session is mock_session
                
                # Verify commit was called
                mock_session.commit.assert_called_once()
                mock_session.close.assert_called_once()
    
    def test_get_session_rolls_back_on_error(self):
        """Test that session rolls back on error."""
        with patch("src.database.db.create_engine"):
            init_db()
            
            with patch("src.database.db._session_factory") as mock_factory:
                mock_session = MagicMock()
                mock_factory.return_value = mock_session
                
                with pytest.raises(ValueError):
                    with get_session() as session:
                        raise ValueError("Test error")
                
                # Verify rollback was called
                mock_session.rollback.assert_called_once()
                mock_session.commit.assert_not_called()
                mock_session.close.assert_called_once()
    
    def test_get_session_always_closes_session(self):
        """Test that session is always closed, even on error."""
        with patch("src.database.db.create_engine"):
            init_db()
            
            with patch("src.database.db._session_factory") as mock_factory:
                mock_session = MagicMock()
                mock_factory.return_value = mock_session
                
                # Test with success
                with get_session():
                    pass
                mock_session.close.assert_called_once()
                
                # Reset and test with error
                mock_session.reset_mock()
                with pytest.raises(ValueError):
                    with get_session():
                        raise ValueError("Test error")
                mock_session.close.assert_called_once()


class TestRetryLogic:
    """Tests for retry logic on transient failures."""
    
    def test_is_transient_error_identifies_operational_errors(self):
        """Test that OperationalError is identified as transient."""
        error = exc.OperationalError("statement", {}, Exception())
        assert _is_transient_error(error) is True
    
    def test_is_transient_error_identifies_connection_errors(self):
        """Test that connection-related errors are identified as transient."""
        transient_messages = [
            "connection refused",
            "connection reset",
            "connection timed out",
            "server closed the connection",
            "could not connect",
            "deadlock",
        ]
        
        for message in transient_messages:
            error = Exception(message)
            assert _is_transient_error(error) is True
    
    def test_is_transient_error_rejects_non_transient_errors(self):
        """Test that non-transient errors are not retried."""
        error = ValueError("Invalid value")
        assert _is_transient_error(error) is False
    
    def test_retry_decorator_retries_on_transient_error(self):
        """Test that retry decorator retries on transient errors."""
        mock_func = Mock()
        mock_func.side_effect = [
            exc.OperationalError("statement", {}, Exception("connection refused")),
            exc.OperationalError("statement", {}, Exception("connection refused")),
            "success",
        ]
        
        decorated = retry_on_transient_error()(mock_func)
        result = decorated()
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_retry_decorator_raises_after_max_attempts(self):
        """Test that retry decorator raises DatabaseRetryError after max attempts."""
        mock_func = Mock()
        mock_func.side_effect = exc.OperationalError(
            "statement", {}, Exception("connection refused")
        )
        
        decorated = retry_on_transient_error(max_retries=2)(mock_func)
        
        with pytest.raises(DatabaseRetryError) as exc_info:
            decorated()
        
        assert "Failed after 3 attempts" in str(exc_info.value)
        assert mock_func.call_count == 3
    
    def test_retry_decorator_does_not_retry_non_transient_errors(self):
        """Test that non-transient errors are not retried."""
        mock_func = Mock()
        mock_func.side_effect = ValueError("Invalid value")
        
        decorated = retry_on_transient_error()(mock_func)
        
        with pytest.raises(ValueError):
            decorated()
        
        # Should only be called once (no retries)
        assert mock_func.call_count == 1
    
    def test_retry_decorator_uses_exponential_backoff(self):
        """Test that retry decorator uses exponential backoff."""
        mock_func = Mock()
        mock_func.side_effect = [
            exc.OperationalError("statement", {}, Exception("connection refused")),
            exc.OperationalError("statement", {}, Exception("connection refused")),
            "success",
        ]
        
        with patch("src.database.db.time.sleep") as mock_sleep:
            decorated = retry_on_transient_error(delay=1.0)(mock_func)
            result = decorated()
            
            assert result == "success"
            # Verify exponential backoff: 1.0, 2.0
            assert mock_sleep.call_count == 2
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert sleep_calls[0] == 1.0  # First retry: delay * 2^0
            assert sleep_calls[1] == 2.0  # Second retry: delay * 2^1
    
class TestHealthCheck:
    """Tests for database health check."""
    
    def test_health_check_raises_error_if_not_initialized(self):
        """Test that health_check raises error if init_db not called."""
        with pytest.raises(DatabaseError) as exc_info:
            health_check()
        
        assert "not initialized" in str(exc_info.value)
    
    def test_health_check_returns_true_on_success(self):
        """Test that health_check returns True when database is accessible."""
        with patch("src.database.db.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_connection = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_connection
            mock_create_engine.return_value = mock_engine
            
            init_db()
            result = health_check()
            
            assert result is True
            mock_connection.execute.assert_called_once()
    
    def test_health_check_retries_on_transient_errors(self):
        """Test that health_check retries on transient errors."""
        with patch("src.database.db.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_connection = MagicMock()
            
            # First attempt fails, second succeeds
            mock_connection.execute.side_effect = [
                exc.OperationalError("statement", {}, Exception("connection refused")),
                None,
            ]
            
            mock_engine.connect.return_value.__enter__.return_value = mock_connection
            mock_create_engine.return_value = mock_engine
            
            init_db()
            
            with patch("src.database.db.time.sleep"):
                result = health_check()
            
            assert result is True
            assert mock_connection.execute.call_count == 2


class TestDatabaseCleanup:
    """Tests for database cleanup."""
    
    def test_close_db_disposes_engine(self):
        """Test that close_db disposes the engine."""
        with patch("src.database.db.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine
            
            init_db()
            close_db()
            
            mock_engine.dispose.assert_called_once()
    
    def test_close_db_clears_global_state(self):
        """Test that close_db clears global engine and session factory."""
        with patch("src.database.db.create_engine"):
            init_db()
            
            # Engine should be accessible
            engine = get_engine()
            assert engine is not None
            
            close_db()
            
            # Engine should no longer be accessible
            with pytest.raises(DatabaseError):
                get_engine()
    
    def test_close_db_handles_uninitialized_state(self):
        """Test that close_db handles being called without initialization."""
        # Should not raise an error
        close_db()
