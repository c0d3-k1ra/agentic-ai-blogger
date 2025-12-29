"""Revision Agent - Apply user feedback to revise articles.

Handles user feedback on article drafts and applies targeted revisions.
Uses LLM to understand feedback and make appropriate changes.

Public API:
    revise_article: Apply user feedback to revise article content
    RevisedArticle: Immutable dataclass containing revised content

Design Principles:
- Accept structured user feedback (not email parsing)
- Use LLM to interpret feedback and apply changes
- Preserve unchanged sections
- Support iterative revision cycles
- Fully testable with mocked LLM

Example:
    >>> feedback = "Make the introduction more engaging and add code examples to section 2"
    >>> revised = await revise_article(original_content, feedback, topic="Python Async")
    >>> print(revised.content)
    # Revised content with changes applied
    >>> print(revised.changes_summary)
    'Updated introduction for better engagement; Added code examples to section 2'
"""

from dataclasses import dataclass

from src.integrations.llm_client import generate_text
from src.integrations.prompts import ARTICLE_REVISION_PROMPT_V1


@dataclass(frozen=True)
class RevisedArticle:
    """A revised article based on user feedback.

    Represents an article that has been revised according to
    specific user feedback.

    Attributes:
        content: Revised markdown content
        changes_summary: Summary of changes made
        word_count: Total word count of revised content
        revision_number: Which revision cycle this is (1, 2, 3, etc.)
    """

    content: str
    changes_summary: str
    word_count: int
    revision_number: int


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


def _extract_changes_summary(response: str) -> str:
    """Extract changes summary from LLM response.

    Args:
        response: LLM response text

    Returns:
        Extracted summary or default message

    Examples:
        >>> text = "Changes: Updated intro\\nRevised Content:\\n..."
        >>> _extract_changes_summary(text)
        'Updated intro'
    """
    # Look for "Changes:" or "Summary:" line
    for line in response.split("\n"):
        line_stripped = line.strip()
        lower = line_stripped.lower()

        if lower.startswith("changes:") or lower.startswith("summary:"):
            # Extract everything after the marker
            colon_idx = line_stripped.index(":")
            summary = line_stripped[colon_idx + 1 :].strip()
            if summary:
                return summary

    return "Applied user feedback"


def _extract_revised_content(response: str, original_content: str) -> str:
    """Extract revised content from LLM response.

    Args:
        response: LLM response text
        original_content: Original article content (fallback)

    Returns:
        Extracted revised content

    Examples:
        >>> response = "Changes: Fixed\\nRevised Content:\\n# New content"
        >>> _extract_revised_content(response, "# Old")
        '# New content'
    """
    # Look for content markers
    content_markers = [
        "revised content:",
        "revised article:",
        "updated content:",
        "new content:",
    ]

    response_lower = response.lower()

    for marker in content_markers:
        if marker in response_lower:
            marker_idx = response_lower.index(marker)
            # Get everything after the marker
            content = response[marker_idx + len(marker) :].strip()
            if content:
                return content

    # If no marker found, try to detect if the response IS the content
    # (starts with markdown heading or has substantial length)
    if response.strip().startswith("#") or len(response.strip()) > 200:
        return response.strip()

    # Fallback: return original
    return original_content


def _build_revision_prompt(topic: str, content: str, feedback: str) -> str:
    """Build prompt for article revision.

    Args:
        topic: Article topic
        content: Current article content
        feedback: User feedback to address

    Returns:
        Formatted prompt string
    """
    # Limit content to 10000 chars for token safety
    return ARTICLE_REVISION_PROMPT_V1.format(
        topic=topic, content=content[:10000], feedback=feedback
    )


async def revise_article(
    content: str,
    feedback: str,
    *,
    topic: str,
    revision_number: int = 1,
    model: str | None = None,
    temperature: float = 0.4,
) -> RevisedArticle:
    """Revise article based on user feedback.

    Uses LLM to interpret feedback and apply appropriate changes
    to the article content while preserving the overall structure
    and quality.

    Args:
        content: Current article markdown content to revise
        feedback: User feedback describing desired changes
        topic: Article topic (for context)
        revision_number: Which revision cycle this is (default: 1)
        model: Optional LLM model override
        temperature: Sampling temperature (default: 0.4 for creativity with control)

    Returns:
        RevisedArticle with updated content and change summary

    Raises:
        ValueError: If inputs invalid or LLM returns empty/invalid response
        LLMRetryExhausted: If LLM generation fails after retries

    Examples:
        >>> content = "# Intro\\nOld intro text..."
        >>> feedback = "Make the intro more engaging"
        >>> revised = await revise_article(content, feedback, topic="Python")
        >>> isinstance(revised, RevisedArticle)
        True
        >>> revised.revision_number
        1

    Notes:
        - Input content is never mutated
        - LLM call is the only side effect
        - Deterministic given same inputs and LLM output
        - Fully testable by mocking generate_text
    """
    # 1. Validate inputs
    if not content or not content.strip():
        raise ValueError("content cannot be empty")

    if not feedback or not feedback.strip():
        raise ValueError("feedback cannot be empty")

    if not topic or not topic.strip():
        raise ValueError("topic cannot be empty")

    if revision_number < 1:
        raise ValueError("revision_number must be >= 1")

    if not 0.0 <= temperature <= 2.0:
        raise ValueError("temperature must be between 0.0 and 2.0")

    # 2. Build revision prompt
    prompt = _build_revision_prompt(topic, content, feedback)

    # 3. Call LLM for revision (only side effect)
    response = await generate_text(prompt, model=model, temperature=temperature)

    # 4. Validate response is not empty
    if not response or not response.strip():
        raise ValueError("LLM returned empty revision")

    # 5. Parse response
    changes_summary = _extract_changes_summary(response)
    revised_content = _extract_revised_content(response, content)

    # 6. Calculate word count
    word_count = _count_words(revised_content)

    # 7. Return structured result
    return RevisedArticle(
        content=revised_content.strip(),
        changes_summary=changes_summary.strip(),
        word_count=word_count,
        revision_number=revision_number,
    )
