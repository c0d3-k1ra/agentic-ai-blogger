"""Tests for arXiv client."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.integrations.search.arxiv_client import fetch_arxiv


@pytest.mark.asyncio
async def test_fetch_arxiv_success():
    """Test successful arXiv fetch."""
    # Create proper mock authors
    author1 = MagicMock()
    author1.name = "Author 1"
    author2 = MagicMock()
    author2.name = "Author 2"

    mock_results = [
        MagicMock(
            entry_id="http://arxiv.org/abs/2301.00001v1",
            title="Test Paper 1",
            summary="Summary 1",
            authors=[author1, author2],
            published=datetime(2023, 1, 1),
            updated=datetime(2023, 1, 2),
            primary_category="cs.AI",
            categories=["cs.AI", "cs.LG"],
            pdf_url="http://arxiv.org/pdf/2301.00001v1",
            links=[MagicMock(href="http://arxiv.org/abs/2301.00001v1")],
        ),
    ]

    with patch("arxiv.Search") as mock_search:
        mock_search.return_value.results.return_value = mock_results

        results = await fetch_arxiv("machine learning", max_results=1)

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["title"] == "Test Paper 1"
        assert results[0]["authors"] == ["Author 1", "Author 2"]
        assert results[0]["primary_category"] == "cs.AI"


@pytest.mark.asyncio
async def test_fetch_arxiv_empty_query():
    """Test error handling for empty query."""
    with pytest.raises(ValueError, match="Query cannot be empty"):
        await fetch_arxiv("")


@pytest.mark.asyncio
async def test_fetch_arxiv_invalid_max_results():
    """Test error handling for invalid max_results."""
    with pytest.raises(ValueError, match="Max results must be positive"):
        await fetch_arxiv("test", max_results=0)


@pytest.mark.asyncio
async def test_fetch_arxiv_empty_results():
    """Test handling of empty results."""
    with patch("arxiv.Search") as mock_search:
        mock_search.return_value.results.return_value = []

        results = await fetch_arxiv("obscure query")

        assert isinstance(results, list)
        assert len(results) == 0
