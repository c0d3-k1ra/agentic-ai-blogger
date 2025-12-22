"""Tests for Hacker News client."""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.search.hackernews_client import fetch_hackernews_top


@pytest.mark.asyncio
async def test_fetch_hackernews_top_success():
    """Test successful Hacker News fetch."""
    mock_story_ids = [1, 2, 3]
    mock_stories = [
        {"id": 1, "title": "Story 1", "by": "user1", "score": 100},
        {"id": 2, "title": "Story 2", "by": "user2", "score": 200},
        {"id": 3, "title": "Story 3", "by": "user3", "score": 300},
    ]

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = mock_client.return_value.__aenter__.return_value

        # Mock the story IDs response
        ids_response = AsyncMock()
        ids_response.raise_for_status = AsyncMock()
        ids_response.json = AsyncMock(return_value=mock_story_ids)

        # Mock individual story responses
        story_responses = []
        for story in mock_stories:
            story_response = AsyncMock()
            story_response.raise_for_status = AsyncMock()
            story_response.json = AsyncMock(return_value=story)
            story_responses.append(story_response)

        mock_instance.get = AsyncMock(side_effect=[ids_response] + story_responses)

        results = await fetch_hackernews_top(limit=3)

        assert isinstance(results, list)
        assert len(results) == 3
        assert results[0]["id"] == 1
        assert results[0]["title"] == "Story 1"


@pytest.mark.asyncio
async def test_fetch_hackernews_top_invalid_limit():
    """Test error handling for invalid limit."""
    with pytest.raises(ValueError, match="Limit must be positive"):
        await fetch_hackernews_top(limit=0)


@pytest.mark.asyncio
async def test_fetch_hackernews_top_empty_results():
    """Test handling of empty results."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = mock_client.return_value.__aenter__.return_value

        ids_response = AsyncMock()
        ids_response.raise_for_status = AsyncMock()
        ids_response.json = AsyncMock(return_value=[])

        mock_instance.get = AsyncMock(return_value=ids_response)

        results = await fetch_hackernews_top(limit=10)

        assert isinstance(results, list)
        assert len(results) == 0
