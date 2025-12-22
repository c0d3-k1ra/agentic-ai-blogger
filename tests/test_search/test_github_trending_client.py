"""Tests for GitHub Trending client."""

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.search.github_trending_client import fetch_github_trending


@pytest.mark.asyncio
async def test_fetch_github_trending_success():
    """Test successful GitHub Trending scrape."""
    mock_html = """
    <html>
        <article class="Box-row">
            <h2><a href="/user/repo1">Test Repo 1</a></h2>
            <p class="col-9">Description 1</p>
            <span class="d-inline-block float-sm-right">100 stars</span>
            <span itemprop="programmingLanguage">Python</span>
        </article>
        <article class="Box-row">
            <h2><a href="/user/repo2">Test Repo 2</a></h2>
            <p class="col-9">Description 2</p>
            <span class="d-inline-block float-sm-right">200 stars</span>
            <span itemprop="programmingLanguage">Python</span>
        </article>
    </html>
    """

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_instance.get = AsyncMock()
        mock_instance.get.return_value.raise_for_status = lambda: None
        mock_instance.get.return_value.text = mock_html

        results = await fetch_github_trending("python")

        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["name"] == "user/repo1"
        assert results[0]["description"] == "Description 1"
        assert results[0]["stars"] == "100 stars"


@pytest.mark.asyncio
async def test_fetch_github_trending_empty_language():
    """Test error handling for empty language."""
    with pytest.raises(ValueError, match="Language cannot be empty"):
        await fetch_github_trending("")


@pytest.mark.asyncio
async def test_fetch_github_trending_empty_results():
    """Test handling of empty results."""
    mock_html = "<html><body>No articles found</body></html>"

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_instance.get = AsyncMock()
        mock_instance.get.return_value.raise_for_status = lambda: None
        mock_instance.get.return_value.text = mock_html

        results = await fetch_github_trending("obscure-language")

        assert isinstance(results, list)
        assert len(results) == 0


@pytest.mark.asyncio
async def test_fetch_github_trending_malformed_html():
    """Test handling of malformed HTML entries."""
    mock_html = """
    <html>
        <article class="Box-row">
            <h2>No link here</h2>
        </article>
        <article class="Box-row">
            <h2><a href="/valid/repo">Valid Repo</a></h2>
            <p class="col-9">Valid Description</p>
        </article>
    </html>
    """

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_instance.get = AsyncMock()
        mock_instance.get.return_value.raise_for_status = lambda: None
        mock_instance.get.return_value.text = mock_html

        results = await fetch_github_trending("python")

        # Should skip malformed entry and return only valid one
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["name"] == "valid/repo"
