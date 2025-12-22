"""Tavily web search client.

Provides raw search results from Tavily API.
"""

import os

import httpx


async def search_tavily(query: str, limit: int = 10) -> list[dict]:
    """Perform a web search using Tavily API.

    Args:
        query: Search query string
        limit: Maximum number of results to return

    Returns:
        List of raw Tavily result dictionaries

    Raises:
        ValueError: If query is empty or API key is missing
        httpx.HTTPError: If API request fails
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY environment variable not set")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": limit,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()  # httpx.json() is synchronous, not async

    # Return raw results array
    return data.get("results", [])
