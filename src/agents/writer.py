"""Writer Agent - Section-level article content generation.

Generates markdown prose content for individual article sections using LLM.
Works with structured inputs from Structure Planner and returns structured output.

Public API:
    write_section: Generate prose content for exactly one article section
    WrittenSection: Immutable dataclass containing generated content and metadata

Design Principles:
- Write exactly one section (not full articles)
- Structured input/output contracts
- No orchestration logic
- No review or revision
- Pure function with minimal side effects (only LLM call)
- Fully testable with mocked LLM

Example:
    >>> outline = generate_outline("Python Async Programming")
    >>> section = outline.sections[0]
    >>> written = await write_section(outline, section, target_words=300)
    >>> print(written.section_title)
    'Introduction to Python Async Programming'
    >>> print(written.word_count)
    287
"""

from dataclasses import dataclass

from src.agents.structure_planner import Outline, Section
from src.integrations.llm_client import generate_text
from src.integrations.prompts import SECTION_WRITING_PROMPT_V1


@dataclass(frozen=True)
class WrittenSection:
    """A written section of an article with metadata.

    Represents markdown prose content for exactly one section.
    Immutable structure using frozen dataclass.

    Attributes:
        section_title: The section title (from Section.title)
        content: Markdown-formatted prose content
        word_count: Number of words in content (computed from text)
    """

    section_title: str
    content: str
    word_count: int


def _count_words(text: str) -> int:
    """Count words in text.

    Simple whitespace-based word counting.
    Includes markdown syntax in count for consistency.

    Args:
        text: Text content (may contain markdown)

    Returns:
        Number of words

    Examples:
        >>> _count_words("Hello world")
        2
        >>> _count_words("# Title\\n\\nParagraph here.")
        4
        >>> _count_words("")
        0
    """
    if not text or not text.strip():
        return 0

    # Split on whitespace, count non-empty tokens
    words = text.split()
    return len(words)


def _build_section_prompt(outline: Outline, section: Section, target_words: int) -> str:
    """Build prompt for writing a specific section.

    Pure function - no side effects, deterministic output.
    Constructs prompt from template with section context.

    Args:
        outline: Complete outline (for topic context)
        section: Section to write
        target_words: Target word count

    Returns:
        Formatted prompt string ready for LLM

    Examples:
        >>> outline = generate_outline("Python")
        >>> section = outline.sections[0]
        >>> prompt = _build_section_prompt(outline, section, 300)
        >>> "Python" in prompt
        True
    """
    # Format subsections as bulleted list
    subsections_list = "\n".join(f"- {sub}" for sub in section.subsections)

    # Fill template with context
    return SECTION_WRITING_PROMPT_V1.format(
        topic=outline.topic,
        section_title=section.title,
        subsections_list=subsections_list,
        target_words=target_words,
    )


def _validate_inputs(outline: Outline, section: Section) -> None:
    """Validate inputs before writing.

    Checks that inputs are valid and that section belongs to outline.

    Args:
        outline: Outline to validate
        section: Section to validate

    Raises:
        ValueError: If inputs are invalid or section not in outline

    Examples:
        >>> outline = generate_outline("Python")
        >>> section = outline.sections[0]
        >>> _validate_inputs(outline, section)  # No error
        >>> _validate_inputs(outline, None)  # Raises ValueError
    """
    if outline is None:
        raise ValueError("outline cannot be None")

    if section is None:
        raise ValueError("section cannot be None")

    # Check section is in outline
    if section not in outline.sections:
        available_titles = [s.title for s in outline.sections]
        raise ValueError(
            f"Section '{section.title}' is not in the provided outline. "
            f"Available sections: {available_titles}"
        )


async def write_section(
    outline: Outline,
    section: Section,
    *,
    target_words: int = 500,
    model: str | None = None,
    temperature: float = 0.7,
) -> WrittenSection:
    """Write prose content for exactly one article section.

    Uses LLM to generate markdown-formatted technical writing for a single
    section within an article outline. Does not write the full article.

    The function:
    1. Validates that section belongs to outline
    2. Builds a detailed prompt with context
    3. Calls LLM via llm_client.generate_text
    4. Validates output is non-empty
    5. Computes word count
    6. Returns structured WrittenSection

    Args:
        outline: Complete article outline (provides context)
        section: Specific section to write (must be in outline.sections)
        target_words: Target word count for section (default: 500, min: 50)
        model: Optional LLM model override (passed to generate_text)
        temperature: Sampling temperature (default: 0.7 for creative writing)

    Returns:
        WrittenSection with generated content and computed word count

    Raises:
        ValueError: If inputs invalid, section not in outline, target_words < 50,
                   temperature out of range, or LLM returns empty content
        LLMRetryExhausted: If LLM generation fails after retries

    Examples:
        >>> outline = generate_outline("Python Async Programming")
        >>> section = outline.sections[0]
        >>> written = await write_section(outline, section, target_words=300)
        >>> isinstance(written, WrittenSection)
        True
        >>> written.section_title == section.title
        True
        >>> written.word_count > 0
        True

    Notes:
        - Input Outline and Section are never mutated (frozen dataclasses)
        - LLM call is the only side effect
        - Same inputs + same LLM output = same WrittenSection (deterministic)
        - Fully testable by mocking generate_text
    """
    # 1. Validate inputs
    _validate_inputs(outline, section)

    if target_words < 50:
        raise ValueError("target_words must be at least 50")

    if not 0.0 <= temperature <= 2.0:
        raise ValueError("temperature must be between 0.0 and 2.0")

    # 2. Build prompt with full context
    prompt = _build_section_prompt(outline, section, target_words)

    # 3. Call LLM (only side effect in this function)
    content = await generate_text(prompt, model=model, temperature=temperature)

    # 4. Validate output is not empty
    if not content or not content.strip():
        raise ValueError("LLM returned empty content")

    # 5. Clean and compute word count
    clean_content = content.strip()
    word_count = _count_words(clean_content)

    # 6. Return structured result
    return WrittenSection(section_title=section.title, content=clean_content, word_count=word_count)
