"""Topic Scout Agent - Pure topic generation.

Generates candidate article topics from a seed topic using template-based
expansion. No LLM calls, no external APIs, no side effects.

Design Principles:
- Deterministic output (same input → same output)
- Keyword expansion for diversity
- Template-based generation
- No external dependencies
- Isolated from workflow logic
"""

from typing import Final

# Template categories for topic generation
# These templates create variations across different article types and skill levels
TOPIC_TEMPLATES: Final[list[str]] = [
    # Beginner-focused
    "Introduction to {topic}",
    "Getting Started with {topic}",
    "{topic} for Beginners",
    "{topic} Fundamentals",
    "Understanding {topic} Basics",
    "{topic} 101",
    "Learn {topic} from Scratch",
    "Your First {topic} Project",
    # Advanced
    "Advanced {topic} Techniques",
    "Mastering {topic}",
    "{topic} Expert Guide",
    "Deep Dive into {topic}",
    "{topic} Advanced Concepts",
    "Professional {topic} Development",
    # Practical/Applied
    "{topic} Best Practices",
    "Production-Ready {topic}",
    "Real-World {topic} Applications",
    "{topic} in Practice",
    "{topic} Tips and Tricks",
    "Building with {topic}",
    "{topic} Project Ideas",
    # Problem-Solving
    "Common {topic} Mistakes to Avoid",
    "Debugging {topic} Issues",
    "{topic} Pitfalls and Solutions",
    "Troubleshooting {topic}",
    "{topic} Error Handling",
    # Comparative
    "{topic} vs Alternatives",
    "When to Use {topic}",
    "Choosing the Right {topic} Approach",
    "{topic} Comparison Guide",
    # Tutorial
    "Building Applications with {topic}",
    "{topic} Step-by-Step Tutorial",
    "Complete {topic} Guide",
    "{topic} Hands-On Tutorial",
    "How to Use {topic}",
    # Performance
    "Optimizing {topic} Performance",
    "{topic} Scalability",
    "{topic} Performance Tuning",
    "{topic} Optimization Guide",
    # Architecture/Design
    "{topic} Design Patterns",
    "{topic} Architecture Guide",
    "Designing with {topic}",
    "{topic} System Design",
    # Testing
    "Testing {topic}",
    "{topic} Testing Strategies",
    "Unit Testing with {topic}",
    # Integration
    "Integrating {topic}",
    "{topic} Integration Patterns",
    "{topic} with Other Tools",
]


def generate_topics(
    seed_topic: str,
    *,
    max_topics: int = 30,
) -> list[str]:
    """Generate related article topics from a seed topic.

    Uses template-based expansion to create topic variations. The algorithm:
    1. Extracts keywords from seed_topic (full phrase + individual tokens)
    2. Applies templates to each keyword candidate
    3. Normalizes whitespace
    4. Removes duplicates while preserving order
    5. Caps output at max_topics

    This is a pure, deterministic function with no side effects or external
    dependencies. It's designed as a placeholder for future LLM-based generation.

    Args:
        seed_topic: The base topic to expand (e.g., "Python Async")
        max_topics: Maximum number of topics to return (default: 30)

    Returns:
        List of unique topic strings, ordered by generation sequence.
        Each topic is non-empty with normalized whitespace.

    Raises:
        ValueError: If seed_topic is empty/whitespace-only or max_topics < 1

    Examples:
        >>> generate_topics("Python", max_topics=5)
        ['Introduction to Python', 'Getting Started with Python', ...]

        >>> generate_topics("Python Async", max_topics=10)
        ['Introduction to Python Async', 'Introduction to Python', ...]

    Design Notes:
        - Single-word seeds: Uses seed as-is
        - Multi-word seeds: Expands to full phrase + individual tokens
        - No randomness: Same input always produces same output
        - No LLM calls: Pure algorithmic generation
        - Thread-safe: No global mutable state
    """
    # Input validation
    if not seed_topic or not seed_topic.strip():
        raise ValueError("seed_topic cannot be empty or whitespace-only")

    if max_topics < 1:
        raise ValueError("max_topics must be at least 1")

    # Generate keyword candidates
    # For "Python Async" → ["Python Async", "Python", "Async"]
    # For "Python" → ["Python"]
    seed_clean = seed_topic.strip()
    tokens = seed_clean.split()

    candidates = [seed_clean]
    if len(tokens) > 1:
        candidates.extend(tokens)

    # Apply templates to all candidates
    topics = []
    for template in TOPIC_TEMPLATES:
        for candidate in candidates:
            # Format template with candidate
            topic = template.format(topic=candidate)

            # Normalize whitespace (remove double spaces, tabs, etc.)
            topic = " ".join(topic.split())

            topics.append(topic)

            # Early exit if we've hit the limit
            if len(topics) >= max_topics:
                break

        if len(topics) >= max_topics:
            break

    # Remove duplicates while preserving order
    seen = set()
    unique_topics = []
    for topic in topics:
        if topic not in seen:
            seen.add(topic)
            unique_topics.append(topic)

    # Cap at max_topics
    return unique_topics[:max_topics]
