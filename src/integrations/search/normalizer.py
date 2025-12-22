"""Search result normalization.

Pure data transformation layer that converts raw source-specific
search results into a canonical normalized schema.

NO business logic, ranking, scoring, or deduplication.
"""

from datetime import datetime
from urllib.parse import quote_plus


def normalize_tavily(results: list[dict]) -> list[dict]:
    """Normalize Tavily search results.

    Args:
        results: List of raw Tavily result dictionaries

    Returns:
        List of normalized records following canonical schema

    Raises:
        ValueError: If results is not a list
    """
    if not isinstance(results, list):
        raise ValueError("Results must be a list")

    normalized = []
    for raw_result in results:
        # Skip if missing required fields
        title = raw_result.get("title", "").strip()
        url = raw_result.get("url", "").strip()

        if not title or not url:
            continue

        # Extract and truncate summary
        summary = raw_result.get("content", "").strip()
        if len(summary) > 500:
            summary = summary[:500]

        # Parse published date if available
        published_at = None
        if raw_result.get("published_date"):
            try:
                published_at = datetime.fromisoformat(
                    raw_result["published_date"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        normalized.append(
            {
                "title": title,
                "summary": summary,
                "url": url,
                "source": "tavily",
                "published_at": published_at,
                "raw": raw_result,
            }
        )

    return normalized


def normalize_hackernews(results: list[dict]) -> list[dict]:
    """Normalize Hacker News results.

    Args:
        results: List of raw HN API story dictionaries

    Returns:
        List of normalized records following canonical schema

    Raises:
        ValueError: If results is not a list
    """
    if not isinstance(results, list):
        raise ValueError("Results must be a list")

    normalized = []
    for raw_result in results:
        # Skip if missing title
        title = raw_result.get("title", "").strip()
        if not title:
            continue

        # HN stories may not have URL (self-posts)
        url = raw_result.get("url", "").strip()
        text = raw_result.get("text", "").strip()

        # Skip if no URL and no text
        if not url and not text:
            continue

        # Use HN item URL if no external URL
        if not url:
            story_id = raw_result.get("id")
            if story_id:
                url = f"https://news.ycombinator.com/item?id={story_id}"
            else:
                continue

        # Use text as summary for self-posts, empty otherwise
        summary = text if text else ""
        if len(summary) > 500:
            summary = summary[:500]

        # Parse unix timestamp
        published_at = None
        if raw_result.get("time"):
            try:
                published_at = datetime.fromtimestamp(raw_result["time"])
            except (ValueError, TypeError, OSError):
                pass

        normalized.append(
            {
                "title": title,
                "summary": summary,
                "url": url,
                "source": "hackernews",
                "published_at": published_at,
                "raw": raw_result,
            }
        )

    return normalized


def normalize_arxiv(results: list[dict]) -> list[dict]:
    """Normalize arXiv paper results.

    Args:
        results: List of raw arXiv paper dictionaries

    Returns:
        List of normalized records following canonical schema

    Raises:
        ValueError: If results is not a list
    """
    if not isinstance(results, list):
        raise ValueError("Results must be a list")

    normalized = []
    for raw_result in results:
        # Skip if missing required fields
        title = raw_result.get("title", "").strip()
        entry_id = raw_result.get("entry_id", "").strip()

        if not title or not entry_id:
            continue

        # Extract and truncate summary
        summary = raw_result.get("summary", "").strip()
        if len(summary) > 500:
            summary = summary[:500]

        # Parse published date
        published_at = None
        if raw_result.get("published"):
            try:
                published_at = datetime.fromisoformat(
                    raw_result["published"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        normalized.append(
            {
                "title": title,
                "summary": summary,
                "url": entry_id,  # arXiv entry_id is the canonical URL
                "source": "arxiv",
                "published_at": published_at,
                "raw": raw_result,
            }
        )

    return normalized


def normalize_github_trending(results: list[dict]) -> list[dict]:
    """Normalize GitHub Trending results.

    Args:
        results: List of raw GitHub repository dictionaries

    Returns:
        List of normalized records following canonical schema

    Raises:
        ValueError: If results is not a list
    """
    if not isinstance(results, list):
        raise ValueError("Results must be a list")

    normalized = []
    for raw_result in results:
        # Skip if missing required fields
        name = raw_result.get("name", "").strip()
        url = raw_result.get("url", "").strip()

        if not name or not url:
            continue

        # Use repo name as title
        title = name

        # Extract and truncate description as summary
        summary = raw_result.get("description", "").strip()
        if len(summary) > 500:
            summary = summary[:500]

        # GitHub Trending has no published date
        published_at = None

        normalized.append(
            {
                "title": title,
                "summary": summary,
                "url": url,
                "source": "github",
                "published_at": published_at,
                "raw": raw_result,
            }
        )

    return normalized


def normalize_google_trends(results: dict) -> list[dict]:
    """Normalize Google Trends results.

    Creates one record per keyword with aggregate trend data.

    Args:
        results: Raw Google Trends dictionary with keywords and data

    Returns:
        List of normalized records following canonical schema

    Raises:
        ValueError: If results is not a dict
    """
    if not isinstance(results, dict):
        raise ValueError("Results must be a dict")

    keywords = results.get("keywords", [])
    if not keywords:
        return []

    normalized = []
    for keyword in keywords:
        if not keyword or not keyword.strip():
            continue

        keyword = keyword.strip()

        # Create deterministic Google Trends URL
        url = f"https://trends.google.com/trends/explore?q={quote_plus(keyword)}"

        # Create summary describing the trend data
        summary = f"Interest data for '{keyword}' over the past 3 months"

        # Title includes keyword
        title = f"Google Trends: {keyword}"

        # No published date for trend data
        published_at = None

        normalized.append(
            {
                "title": title,
                "summary": summary,
                "url": url,
                "source": "google_trends",
                "published_at": published_at,
                "raw": results,  # Full aggregate payload for all keywords
            }
        )

    return normalized
