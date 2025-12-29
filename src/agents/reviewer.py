"""Reviewer Agent - Article review and SEO optimization.

Reviews article content for quality, correctness, and SEO optimization.
Generates optimized titles, subtitles, tags, and polished content.

Public API:
    review_article: Review and optimize a complete article
    ReviewedArticle: Immutable dataclass containing polished content and SEO metadata

Design Principles:
- Review complete articles (all sections combined)
- Multi-aspect review (grammar, technical accuracy, SEO, readability)
- Structured input/output contracts
- Pure function with minimal side effects (only LLM call)
- Fully testable with mocked LLM

Example:
    >>> outline = generate_outline("Python Async Programming")
    >>> article_content = "..."  # Combined sections
    >>> reviewed = await review_article(outline.topic, article_content)
    >>> print(reviewed.seo_title)
    'Mastering Python Async Programming: A Complete Guide'
    >>> len(reviewed.tags)
    5
"""

from dataclasses import dataclass

from src.integrations.llm_client import generate_text
from src.integrations.prompts import ARTICLE_REVIEW_PROMPT_V1


@dataclass(frozen=True)
class ReviewedArticle:
    """A reviewed article with polished content and SEO metadata.

    Represents a complete article that has been reviewed for quality,
    correctness, and SEO optimization.

    Attributes:
        polished_content: Improved markdown content with corrections
        seo_title: Optimized title for SEO (50-60 characters)
        seo_subtitle: Engaging subtitle/description (120-160 characters)
        tags: List of relevant tags (5-7 tags recommended)
        word_count: Total word count of polished content
        readability_score: Estimated readability level (e.g., "High School", "College")
        improvements_made: Summary of changes/improvements
    """

    polished_content: str
    seo_title: str
    seo_subtitle: str
    tags: tuple[str, ...]
    word_count: int
    readability_score: str
    improvements_made: str


def _count_words(text: str) -> int:
    """Count words in text.

    Args:
        text: Text content (may contain markdown)

    Returns:
        Number of words

    Examples:
        >>> _count_words("Hello world")
        2
        >>> _count_words("")
        0
    """
    if not text or not text.strip():
        return 0

    words = text.split()
    return len(words)


def _extract_tags_from_response(response: str) -> list[str]:
    """Extract tags from LLM response.

    Looks for tags in various formats:
    - Tags: tag1, tag2, tag3
    - #tag1 #tag2 #tag3
    - Comma-separated list

    Args:
        response: LLM response containing tags

    Returns:
        List of extracted tags (cleaned and deduplicated)

    Examples:
        >>> _extract_tags_from_response("Tags: python, async, programming")
        ['python', 'async', 'programming']
    """
    tags = []

    # Look for "Tags:" line
    for line in response.split("\n"):
        line_lower = line.lower().strip()
        if line_lower.startswith("tags:"):
            # Extract everything after "Tags:"
            tags_str = line[5:].strip()
            # Split by comma or semicolon
            tags = [t.strip().strip("#").lower() for t in tags_str.replace(";", ",").split(",")]
            break

    # Fallback: look for hashtags
    if not tags:
        import re

        hashtags = re.findall(r"#(\w+)", response)
        tags = [tag.lower() for tag in hashtags]

    # Clean and deduplicate
    tags = [tag for tag in tags if tag and len(tag) > 1]
    seen = set()
    unique_tags = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)

    return unique_tags[:7]  # Limit to 7 tags


def _extract_field(response: str, field_name: str) -> str:
    """Extract a specific field from LLM response.

    Args:
        response: LLM response text
        field_name: Name of field to extract (e.g., "Title", "Subtitle")

    Returns:
        Extracted field value or empty string if not found

    Examples:
        >>> text = "Title: My Great Article\\nContent here"
        >>> _extract_field(text, "Title")
        'My Great Article'
    """
    for line in response.split("\n"):
        line_stripped = line.strip()
        if line_stripped.lower().startswith(f"{field_name.lower()}:"):
            # Extract everything after the field name
            value = line_stripped[len(field_name) + 1 :].strip()
            # Remove quotes if present
            value = value.strip('"').strip("'")
            return value

    return ""


def _build_review_prompt(topic: str, content: str, min_tags: int = 5, max_tags: int = 7) -> str:
    """Build prompt for article review.

    Args:
        topic: Article topic
        content: Full article content to review
        min_tags: Minimum number of tags to generate
        max_tags: Maximum number of tags to generate

    Returns:
        Formatted prompt string
    """
    # Limit content to 8000 chars for token safety
    return ARTICLE_REVIEW_PROMPT_V1.format(
        topic=topic, content=content[:8000], min_tags=min_tags, max_tags=max_tags
    )


async def review_article(
    topic: str,
    content: str,
    *,
    min_tags: int = 5,
    max_tags: int = 7,
    model: str | None = None,
    temperature: float = 0.3,
) -> ReviewedArticle:
    """Review and optimize a complete article.

    Performs comprehensive review including:
    1. Grammar and spelling correction
    2. Technical accuracy check
    3. SEO optimization (title, subtitle, tags)
    4. Readability improvements
    5. Content polishing

    Args:
        topic: Article topic (for context and SEO)
        content: Full article markdown content to review
        min_tags: Minimum number of tags to generate (default: 5)
        max_tags: Maximum number of tags to generate (default: 7)
        model: Optional LLM model override
        temperature: Sampling temperature (default: 0.3 for precision)

    Returns:
        ReviewedArticle with polished content and SEO metadata

    Raises:
        ValueError: If inputs invalid or LLM returns empty/invalid response
        LLMRetryExhausted: If LLM generation fails after retries

    Examples:
        >>> article_text = "# Introduction\\nPython async..."
        >>> reviewed = await review_article("Python Async", article_text)
        >>> isinstance(reviewed, ReviewedArticle)
        True
        >>> len(reviewed.tags) >= 5
        True

    Notes:
        - Input content is never mutated
        - LLM call is the only side effect
        - Deterministic given same inputs and LLM output
        - Fully testable by mocking generate_text
    """
    # 1. Validate inputs
    if not topic or not topic.strip():
        raise ValueError("topic cannot be empty")

    if not content or not content.strip():
        raise ValueError("content cannot be empty")

    if min_tags < 1 or max_tags < min_tags:
        raise ValueError("Invalid tag limits: min_tags must be >= 1 and max_tags >= min_tags")

    if not 0.0 <= temperature <= 2.0:
        raise ValueError("temperature must be between 0.0 and 2.0")

    # 2. Build review prompt
    prompt = _build_review_prompt(topic, content, min_tags, max_tags)

    # 3. Call LLM for review (only side effect)
    response = await generate_text(prompt, model=model, temperature=temperature)

    # 4. Validate response is not empty
    if not response or not response.strip():
        raise ValueError("LLM returned empty review")

    # 5. Parse LLM response to extract fields
    # Expected format:
    # Title: ...
    # Subtitle: ...
    # Tags: tag1, tag2, tag3
    # Readability: ...
    # Improvements: ...
    # Polished Content:
    # [content here]

    seo_title = _extract_field(response, "Title")
    seo_subtitle = _extract_field(response, "Subtitle")
    tags_list = _extract_tags_from_response(response)
    readability = _extract_field(response, "Readability") or "Not specified"
    improvements = _extract_field(response, "Improvements") or "General improvements made"

    # Extract polished content (everything after "Polished Content:" or "Content:")
    polished_content = content  # Default to original
    content_markers = ["polished content:", "content:", "revised content:"]
    response_lower = response.lower()

    for marker in content_markers:
        if marker in response_lower:
            marker_idx = response_lower.index(marker)
            # Get everything after the marker
            polished_content = response[marker_idx + len(marker) :].strip()
            break

    # 6. Validate extracted data
    if not seo_title:
        # Fallback: use topic
        seo_title = f"{topic}: A Comprehensive Guide"

    if not seo_subtitle:
        # Fallback: create from topic
        seo_subtitle = f"Explore {topic} with practical examples and expert insights"

    if len(tags_list) < min_tags:
        # Fallback: generate basic tags from topic
        topic_words = topic.lower().split()
        # Add unique topic words until we reach min_tags
        for word in topic_words:
            if word not in tags_list and len(tags_list) < min_tags:
                tags_list.append(word)

        # If still not enough, add generic tags
        generic_tags = ["tutorial", "guide", "programming", "development", "tech"]
        for tag in generic_tags:
            if tag not in tags_list and len(tags_list) < min_tags:
                tags_list.append(tag)

    # 7. Calculate word count
    word_count = _count_words(polished_content)

    # 8. Return structured result
    return ReviewedArticle(
        polished_content=polished_content.strip(),
        seo_title=seo_title.strip(),
        seo_subtitle=seo_subtitle.strip(),
        tags=tuple(tags_list[:max_tags]),
        word_count=word_count,
        readability_score=readability.strip(),
        improvements_made=improvements.strip(),
    )
