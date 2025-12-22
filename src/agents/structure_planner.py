"""Structure Planner Agent - Deterministic article outline generation.

Generates structured article outlines using template-based logic without LLM calls.
Produces consistent, high-quality outlines suitable for technical writing.

Design Principles:
- Deterministic output (same topic → same outline)
- True immutability (tuples, not lists)
- Template-based generation
- Smart section adaptation
- No duplicate words in titles
- Guaranteed intro + conclusion structure

Example:
    >>> outline = generate_outline("Advanced Python Async Patterns")
    >>> outline.topic
    'Advanced Python Async Patterns'
    >>> len(outline.sections)
    6
    >>> outline.sections[0].title
    'Introduction to Advanced Python Async Patterns'
"""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class Section:
    """A section in an article outline with subsections.

    Immutable structure representing a major section of an article.
    Uses tuples for true immutability.

    Attributes:
        title: Section heading
        subsections: Tuple of subsection titles
    """

    title: str
    subsections: tuple[str, ...]


@dataclass(frozen=True)
class Outline:
    """Complete article outline structure.

    Immutable representation of an entire article plan.

    Attributes:
        topic: The article topic
        sections: Tuple of Section objects in logical order
    """

    topic: str
    sections: tuple[Section, ...]


# Section templates with minimal topic repetition
# Only "introduction" first subsection uses {topic}
SECTION_TEMPLATES: Final[dict[str, dict]] = {
    "introduction": {
        "title": "Introduction to {topic}",
        "subsections": [
            "What is {topic}?",  # Only subsection with {topic}
            "Why It Matters",
            "Who Should Read This",
            "Article Overview",
        ],
    },
    "fundamentals": {
        "title": "Understanding the Fundamentals",
        "subsections": ["Core Concepts", "Key Terminology", "Basic Examples", "Mental Models"],
    },
    "advanced": {
        "title": "Advanced Techniques",
        "subsections": [
            "Complex Scenarios",
            "Performance Optimization",
            "Design Patterns",
            "Real-World Applications",
        ],
    },
    "practical": {
        "title": "Practical Implementation",
        "subsections": [
            "Step-by-Step Tutorial",
            "Code Examples",
            "Common Use Cases",
            "Integration Strategies",
        ],
    },
    "pitfalls": {
        "title": "Common Pitfalls and Best Practices",
        "subsections": [
            "Mistakes to Avoid",
            "Best Practices Checklist",
            "Debugging Strategies",
            "Performance Tips",
        ],
    },
    "conclusion": {
        "title": "Conclusion and Next Steps",
        "subsections": ["Key Takeaways", "Further Resources", "Community Support", "Future Trends"],
    },
}


def _normalize_title(title: str) -> str:
    """Remove consecutive duplicate words (case-insensitive).

    Prevents awkward titles like "Advanced Advanced Python" that occur
    when both topic and template contain the same word.

    Args:
        title: The title to normalize

    Returns:
        Title with consecutive duplicates removed

    Examples:
        >>> _normalize_title("Advanced Advanced Python")
        'Advanced Python'
        >>> _normalize_title("The the Guide to Python")
        'The Guide to Python'
        >>> _normalize_title("Python Python Python")
        'Python'
        >>> _normalize_title("Introduction to Introduction")
        'Introduction to Introduction'  # Non-adjacent, preserved
    """
    words = title.split()
    deduped = []

    for word in words:
        # Only add if it's different from the previous word (case-insensitive)
        if not deduped or word.lower() != deduped[-1].lower():
            deduped.append(word)

    return " ".join(deduped)


def _determine_sections(topic: str, max_sections: int) -> list[str]:
    """Determine which sections to include based on topic and constraints.

    Always includes:
    - Introduction (first)
    - Conclusion (last)

    Middle sections selected based on:
    - Available slots (max_sections - 2)
    - Topic keywords

    Args:
        topic: The article topic (cleaned)
        max_sections: Maximum total sections allowed

    Returns:
        List of section type keys in order

    Examples:
        >>> _determine_sections("Python", 3)
        ['introduction', 'fundamentals', 'conclusion']
        >>> _determine_sections("Advanced Python", 5)
        ['introduction', 'fundamentals', 'advanced', 'pitfalls', 'conclusion']
    """
    # Reserved sections (always included)
    RESERVED = ["introduction", "conclusion"]

    # Calculate available slots for middle content
    available_slots = max_sections - len(RESERVED)

    # Build middle sections based on available space and topic
    middle = []
    topic_lower = topic.lower()

    # Priority 1: Fundamentals (unless severely constrained)
    if available_slots >= 1:
        middle.append("fundamentals")

    # Priority 2: Advanced OR Practical (keyword-driven)
    if available_slots >= 2:
        if any(kw in topic_lower for kw in ["advanced", "deep", "expert", "mastering"]):
            middle.append("advanced")
        else:
            middle.append("practical")

    # Priority 3: Pitfalls
    if available_slots >= 3:
        middle.append("pitfalls")

    # Priority 4: Add the other (practical/advanced) if room
    if available_slots >= 4:
        if "advanced" in middle:
            middle.append("practical")
        else:
            middle.append("advanced")

    # Cap middle sections to available slots
    middle = middle[:available_slots]

    # Assemble: intro + middle + conclusion
    return ["introduction", *middle, "conclusion"]


def _generate_section(section_type: str, topic: str) -> Section:
    """Generate a single section with subsections.

    Applies topic to title template, normalizes to remove duplicates,
    and handles special subsection formatting for introduction.

    Args:
        section_type: Key into SECTION_TEMPLATES
        topic: The article topic

    Returns:
        Immutable Section object

    Examples:
        >>> s = _generate_section("introduction", "Python")
        >>> s.title
        'Introduction to Python'
        >>> s.subsections[0]
        'What is Python?'
    """
    template = SECTION_TEMPLATES[section_type]

    # Generate and normalize title
    title = template["title"].format(topic=topic)
    title = _normalize_title(title)

    # Handle subsections (special case for introduction)
    if section_type == "introduction":
        # First subsection gets {topic}, rest are generic
        subsections = [template["subsections"][0].format(topic=topic)]
        subsections.extend(template["subsections"][1:])
    else:
        # No topic injection needed
        subsections = template["subsections"].copy()

    # Normalize all subsections and convert to tuple
    normalized_subs = [_normalize_title(sub) for sub in subsections]

    return Section(title=title, subsections=tuple(normalized_subs))


def generate_outline(topic: str, *, max_sections: int = 6) -> Outline:
    """Generate a structured article outline.

    Pure deterministic function that creates a logical article structure
    using template-based generation. No LLM calls or external dependencies.

    The outline always includes:
    - Introduction (first)
    - Core content sections (middle, varies by topic)
    - Conclusion (last)

    Design guarantees:
    - Same topic → same outline (deterministic)
    - No duplicate adjacent words in titles
    - True immutability (tuples throughout)
    - Input never mutated
    - No side effects

    Args:
        topic: Article topic string (e.g., "Advanced Python Async Patterns")
        max_sections: Maximum sections to include (must be ≥ 2)

    Returns:
        Immutable Outline object with ordered sections

    Raises:
        ValueError: If topic is empty/whitespace or max_sections < 2

    Examples:
        >>> outline = generate_outline("Python Async Programming")
        >>> outline.topic
        'Python Async Programming'
        >>> len(outline.sections)
        6
        >>> outline.sections[0].title
        'Introduction to Python Async Programming'
        >>> outline.sections[-1].title
        'Conclusion and Next Steps'

        >>> outline = generate_outline("Python", max_sections=3)
        >>> [s.title for s in outline.sections]
        ['Introduction to Python', 'Understanding the Fundamentals',
         'Conclusion and Next Steps']
    """
    # Validate topic
    if not topic or not topic.strip():
        raise ValueError("topic cannot be empty")

    # Validate max_sections (need room for intro + conclusion)
    if max_sections < 2:
        raise ValueError("max_sections must be at least 2 (intro + conclusion)")

    # Clean topic
    clean_topic = topic.strip()

    # Determine section structure
    section_types = _determine_sections(clean_topic, max_sections)

    # Generate all sections
    sections = [_generate_section(section_type, clean_topic) for section_type in section_types]

    # Return immutable outline
    return Outline(topic=clean_topic, sections=tuple(sections))
