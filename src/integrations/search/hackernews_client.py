"""Hacker News client.

Fetches top stories from Hacker News API.
"""

import httpx


async def fetch_hackernews_top(limit: int = 30) -> list[dict]:
    """Fetch top Hacker News stories.

    Args:
        limit: Maximum number of stories to return

    Returns:
        List of raw HN API story dictionaries

    Raises:
        httpx.HTTPError: If API request fails
    """
    if limit <= 0:
        raise ValueError("Limit must be positive")

    async with httpx.AsyncClient() as client:
        # Get list of top story IDs
        response = await client.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=30.0,
        )
        response.raise_for_status()
        story_ids = (await response.json())[:limit]

        # Fetch full story data for each ID
        stories = []
        for story_id in story_ids:
            story_response = await client.get(
                f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                timeout=30.0,
            )
            story_response.raise_for_status()
            story_data = await story_response.json()
            if story_data:
                stories.append(story_data)

    return stories
