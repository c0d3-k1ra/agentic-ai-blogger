"""Tests for Tavily search client."""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.integrations.search.tavily_client import search_tavily


@pytest.mark.asyncio
async def test_search_tavily_success():
    """Test successful Tavily search."""
    mock_response = {
        "results": [
            {"title": "Result 1", "url": "https://example.com/1", "content": "Content 1"},
            {"title": "Result 2", "url": "https://example.com/2", "content": "Content 2"},
        ]
    }

    with (
        patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}),
        patch("httpx.AsyncClient") as mock_client,
    ):
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_response_obj = AsyncMock()
        mock_response_obj.raise_for_status = Mock()  # httpx.raise_for_status() is synchronous
        mock_response_obj.json = Mock(return_value=mock_response)  # httpx.json() is synchronous
        mock_instance.post = AsyncMock(return_value=mock_response_obj)

        results = await search_tavily("test query", limit=10)

        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["title"] == "Result 1"


@pytest.mark.asyncio
async def test_search_tavily_empty_query():
    """Test error handling for empty query."""
    with pytest.raises(ValueError, match="Query cannot be empty"):
        await search_tavily("")


@pytest.mark.asyncio
async def test_search_tavily_missing_api_key():
    """Test error handling for missing API key."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="TAVILY_API_KEY"):
            await search_tavily("test query")


@pytest.mark.asyncio
async def test_search_tavily_empty_results():
    """Test handling of empty results."""
    with (
        patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}),
        patch("httpx.AsyncClient") as mock_client,
    ):
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_response_obj = AsyncMock()
        mock_response_obj.raise_for_status = Mock()  # httpx.raise_for_status() is synchronous
        mock_response_obj.json = Mock(return_value={"results": []})  # httpx.json() is synchronous
        mock_instance.post = AsyncMock(return_value=mock_response_obj)

        results = await search_tavily("obscure query")

        assert isinstance(results, list)
        assert len(results) == 0
