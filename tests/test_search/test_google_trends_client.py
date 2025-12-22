"""Tests for Google Trends client."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.integrations.search.google_trends_client import fetch_google_trends


@pytest.mark.asyncio
async def test_fetch_google_trends_success():
    """Test successful Google Trends fetch."""
    mock_df = pd.DataFrame(
        {
            "AI": [50, 60, 70],
            "ML": [40, 50, 60],
            "isPartial": [False, False, False],
        }
    )

    with patch("src.integrations.search.google_trends_client.TrendReq") as mock_trends:
        mock_instance = MagicMock()
        mock_instance.interest_over_time.return_value = mock_df
        mock_trends.return_value = mock_instance

        results = await fetch_google_trends(["AI", "ML"])

        assert isinstance(results, dict)
        assert "keywords" in results
        assert "data" in results
        assert results["keywords"] == ["AI", "ML"]
        assert isinstance(results["data"], list)
        assert len(results["data"]) == 3


@pytest.mark.asyncio
async def test_fetch_google_trends_empty_keywords():
    """Test error handling for empty keywords list."""
    with pytest.raises(ValueError, match="Keywords list cannot be empty"):
        await fetch_google_trends([])


@pytest.mark.asyncio
async def test_fetch_google_trends_too_many_keywords():
    """Test error handling for too many keywords."""
    with pytest.raises(ValueError, match="maximum 5 keywords"):
        await fetch_google_trends(["k1", "k2", "k3", "k4", "k5", "k6"])


@pytest.mark.asyncio
async def test_fetch_google_trends_empty_results():
    """Test handling of empty results."""
    mock_df = pd.DataFrame()

    with patch("src.integrations.search.google_trends_client.TrendReq") as mock_trends:
        mock_instance = MagicMock()
        mock_instance.interest_over_time.return_value = mock_df
        mock_trends.return_value = mock_instance

        results = await fetch_google_trends(["obscure term"])

        assert isinstance(results, dict)
        assert results["keywords"] == ["obscure term"]
        assert results["data"] == []


@pytest.mark.asyncio
async def test_fetch_google_trends_rate_limit_retry():
    """Test retry logic for rate limiting (429 errors)."""
    mock_df = pd.DataFrame(
        {
            "AI": [50, 60, 70],
            "isPartial": [False, False, False],
        }
    )

    with patch("src.integrations.search.google_trends_client.TrendReq") as mock_trends:
        mock_instance = MagicMock()
        # First two calls raise 429, third succeeds
        mock_instance.interest_over_time.side_effect = [
            Exception("429 Too Many Requests"),
            Exception("Rate limit exceeded"),
            mock_df,
        ]
        mock_trends.return_value = mock_instance

        # Should succeed after retries (with short delays for testing)
        results = await fetch_google_trends(["AI"], max_retries=3, base_delay=0.1)

        assert isinstance(results, dict)
        assert results["keywords"] == ["AI"]
        assert len(results["data"]) == 3
        # Verify it was called 3 times (2 failures + 1 success)
        assert mock_instance.interest_over_time.call_count == 3


@pytest.mark.asyncio
async def test_fetch_google_trends_rate_limit_exhausted():
    """Test failure when rate limit retries are exhausted."""
    with patch("src.integrations.search.google_trends_client.TrendReq") as mock_trends:
        mock_instance = MagicMock()
        # All calls raise 429
        mock_instance.interest_over_time.side_effect = Exception("429 Too Many Requests")
        mock_trends.return_value = mock_instance

        # Should fail after all retries
        with pytest.raises(Exception, match="rate limit exceeded"):
            await fetch_google_trends(["AI"], max_retries=2, base_delay=0.1)


@pytest.mark.asyncio
async def test_fetch_google_trends_non_rate_limit_error():
    """Test immediate failure for non-rate-limit errors."""
    with patch("src.integrations.search.google_trends_client.TrendReq") as mock_trends:
        mock_instance = MagicMock()
        # Raise a non-rate-limit error
        mock_instance.interest_over_time.side_effect = Exception("Network error")
        mock_trends.return_value = mock_instance

        # Should fail immediately without retries
        with pytest.raises(Exception, match="Network error"):
            await fetch_google_trends(["AI"], max_retries=3)

        # Should only be called once (no retries for non-rate-limit errors)
        assert mock_instance.interest_over_time.call_count == 1
