"""Google Trends client.

Fetches interest data from Google Trends with rate limiting and retry logic.
"""

import asyncio
import logging
from typing import Optional

from pytrends.request import TrendReq

logger = logging.getLogger(__name__)


async def fetch_google_trends(
    keywords: list[str],
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> dict:
    """Fetch Google Trends interest data with rate limiting and retry logic.

    Args:
        keywords: List of keywords to query (max 5)
        max_retries: Maximum number of retry attempts for rate limiting (default: 3)
        base_delay: Base delay in seconds between retries (default: 2.0)

    Returns:
        Raw pytrends output dictionary with interest over time data

    Raises:
        ValueError: If keywords list is empty or has more than 5 items
        Exception: If all retry attempts fail
    """
    if not keywords:
        raise ValueError("Keywords list cannot be empty")

    if len(keywords) > 5:
        raise ValueError("Google Trends supports maximum 5 keywords")

    last_exception: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            # Add delay before request (except first attempt)
            if attempt > 0:
                # Exponential backoff: 2s, 4s, 8s, etc.
                delay = base_delay * (2**attempt)
                logger.warning(
                    f"Rate limited by Google Trends. Retrying in {delay}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                await asyncio.sleep(delay)

            # Initialize pytrends with timeout
            pytrends = TrendReq(
                hl="en-US",
                tz=360,
                timeout=(10, 30),  # (connect timeout, read timeout)
                retries=0,  # We handle retries ourselves
                backoff_factor=0,
            )

            # Build payload
            pytrends.build_payload(
                keywords,
                cat=0,
                timeframe="today 3-m",
                geo="",
                gprop="",
            )

            # Get interest over time
            interest_df = pytrends.interest_over_time()

            # Convert DataFrame to dictionary
            if interest_df.empty:
                return {"keywords": keywords, "data": []}

            # Convert to list of dictionaries with date and values
            result = {
                "keywords": keywords,
                "data": interest_df.to_dict(orient="records"),
            }

            return result

        except Exception as e:
            last_exception = e
            error_msg = str(e).lower()

            # Check if it's a rate limit error (429 or related messages)
            is_rate_limit = (
                "429" in error_msg or "too many requests" in error_msg or "rate limit" in error_msg
            )

            if is_rate_limit and attempt < max_retries - 1:
                # Continue to next retry attempt
                continue
            elif is_rate_limit:
                # Last attempt failed with rate limit
                logger.error(f"Google Trends rate limit exceeded after {max_retries} attempts")
                raise Exception(
                    f"Google Trends rate limit exceeded. Please try again later. "
                    f"Keywords: {keywords}"
                ) from e
            else:
                # Non-rate-limit error, fail immediately
                logger.error(f"Google Trends error: {e}")
                raise

    # Should not reach here, but just in case
    raise last_exception or Exception("Unknown error in fetch_google_trends")
