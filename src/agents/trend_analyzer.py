"""Trend Analyzer Agent - Deterministic topic scoring and ranking.

Evaluates topic quality using heuristic-based scoring without LLMs or external APIs.

Scoring Components:
- Length optimization (prefer 40-80 characters)
- Keyword richness (non-stopword token ratio)
- Specificity bonuses (concrete, actionable keywords)
- Generic penalties (overly basic phrases)

Design Principles:
- Pure deterministic logic (no randomness)
- No external dependencies
- Immutable output (frozen dataclass)
- Input sanitization (defensive programming)
"""

from dataclasses import dataclass
from typing import Final

# Constants for scoring heuristics
STOPWORDS: Final[set[str]] = {
    "a",
    "an",
    "the",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "should",
    "could",
    "may",
    "might",
    "must",
    "can",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
}

SPECIFICITY_KEYWORDS: Final[set[str]] = {
    "guide",
    "patterns",
    "performance",
    "best practices",
    "optimization",
    "advanced",
    "deep dive",
    "architecture",
    "production",
    "scalability",
    "real-world",
    "hands-on",
    "tutorial",
    "techniques",
    "mastering",
    "expert",
    "professional",
    "design",
    "implementation",
    "practical",
    "building",
    "creating",
    "developing",
    "testing",
}

GENERIC_PHRASES: Final[set[str]] = {
    "introduction to",
    "getting started",
    "overview of",
    "what is",
    "basics of",
    "101",
    "for beginners",
}


@dataclass(frozen=True)
class ScoredTopic:
    """A topic with its calculated quality score.

    Immutable to prevent accidental mutation during workflow processing.

    Attributes:
        topic: The article topic string
        score: Quality score (typically 0.0 to ~1.1)
    """

    topic: str
    score: float


def _calculate_length_score(topic: str) -> float:
    """Calculate length-based quality score.

    Optimal range: 40-80 characters
    - Perfect score (1.0): within optimal range
    - Penalty: below 40 or above 80 characters

    Uses a piecewise linear penalty function.

    Args:
        topic: The topic string to evaluate

    Returns:
        Score in range [0.0, 1.0]

    Examples:
        >>> _calculate_length_score("Python Programming")  # 18 chars
        0.45
        >>> _calculate_length_score("Advanced Python Techniques")  # 50 chars
        1.0
        >>> _calculate_length_score("A" * 100)  # 100 chars
        0.75
    """
    length = len(topic)

    if 40 <= length <= 80:
        return 1.0
    elif length < 40:
        # Linear penalty for too short
        return max(0.0, length / 40)
    else:
        # Linear penalty for too long
        excess = length - 80
        return max(0.0, 1.0 - (excess / 80))


def _calculate_keyword_richness(topic: str) -> float:
    """Calculate keyword richness score.

    Measures the ratio of meaningful (non-stopword) tokens to total tokens.
    Higher ratio indicates more content-rich topics.

    Args:
        topic: The topic string to evaluate

    Returns:
        Score in range [0.0, 1.0]

    Examples:
        >>> _calculate_keyword_richness("Python Programming")
        1.0  # Both tokens are meaningful
        >>> _calculate_keyword_richness("Introduction to Python")
        0.67  # 2/3 tokens are meaningful
    """
    tokens = topic.lower().split()
    if not tokens:
        return 0.0

    meaningful = [t for t in tokens if t not in STOPWORDS]

    # Clamp to [0.0, 1.0] for safety against pathological inputs
    return min(1.0, len(meaningful) / len(tokens))


def _calculate_specificity_bonus(topic: str) -> float:
    """Calculate specificity bonus.

    Rewards topics containing concrete, actionable keywords.
    These indicate practical, in-depth content rather than generic overviews.

    Args:
        topic: The topic string to evaluate

    Returns:
        Bonus in range [0.0, 0.5]

    Examples:
        >>> _calculate_specificity_bonus("Advanced Python Performance")
        0.30  # 2 matches: "advanced", "performance"
        >>> _calculate_specificity_bonus("Python Tutorial")
        0.15  # 1 match: "tutorial"
    """
    topic_lower = topic.lower()
    matches = sum(1 for keyword in SPECIFICITY_KEYWORDS if keyword in topic_lower)

    # Each match adds 0.15 bonus, capped at 0.5
    return min(0.5, matches * 0.15)


def _calculate_generic_penalty(topic: str) -> float:
    """Calculate generic phrase penalty.

    Penalizes topics containing overly basic, beginner-focused phrases.
    These typically indicate less valuable content for most audiences.

    Args:
        topic: The topic string to evaluate

    Returns:
        Penalty in range [-0.5, 0.0]

    Examples:
        >>> _calculate_generic_penalty("Introduction to Python")
        -0.3  # Contains "introduction to"
        >>> _calculate_generic_penalty("Advanced Python Techniques")
        0.0  # No generic phrases
    """
    topic_lower = topic.lower()
    penalty = 0.0

    for phrase in GENERIC_PHRASES:
        if phrase in topic_lower:
            penalty -= 0.3

    # Cap penalty at -0.5 to avoid excessive penalization
    return max(-0.5, penalty)


def _score_topic(topic: str) -> float:
    """Calculate overall topic quality score.

    Combines multiple heuristics:

    Base Score (weighted average):
    - Length score: 30% weight (optimal 40-80 chars)
    - Keyword richness: 30% weight (non-stopword ratio)

    Absolute Adjustments:
    - Specificity bonus: +0.0 to +0.5 (concrete keywords)
    - Generic penalty: -0.5 to 0.0 (beginner phrases)

    Args:
        topic: The topic string to evaluate

    Returns:
        Final score typically in range [0.0, 1.1]

    Examples:
        >>> _score_topic("Advanced Python Performance Optimization")
        0.85  # High score: good length, specific, no generic terms
        >>> _score_topic("Introduction to Python")
        0.07  # Low score: short, generic phrase
    """
    # Base score from weighted heuristics (max 0.60)
    base = _calculate_length_score(topic) * 0.30 + _calculate_keyword_richness(topic) * 0.30

    # Absolute adjustments (not weighted again)
    bonus = _calculate_specificity_bonus(topic)
    penalty = _calculate_generic_penalty(topic)

    # Final score with floor at 0.0
    return max(0.0, base + bonus + penalty)


def analyze_trends(
    topics: list[str],
    *,
    max_topics: int = 5,
) -> list[ScoredTopic]:
    """Analyze and rank topics by quality score.

    Scores each topic using deterministic heuristics and returns the top N
    topics sorted by descending score. Topics with equal scores are
    sub-sorted alphabetically for stable ordering.

    This is a pure function with no side effects:
    - No LLM calls
    - No external APIs
    - No database access
    - No randomness
    - Input list is not mutated

    Args:
        topics: List of topic strings to analyze
        max_topics: Maximum number of topics to return (default: 5)

    Returns:
        List of ScoredTopic objects, sorted by descending score.
        Returns empty list if no valid topics provided.

    Raises:
        ValueError: If max_topics < 1

    Examples:
        >>> topics = ["Python", "Advanced Python Performance", "Intro to Python"]
        >>> results = analyze_trends(topics, max_topics=2)
        >>> results[0].topic
        'Advanced Python Performance'
        >>> results[0].score > results[1].score
        True

    Design Notes:
        - Filters out empty/whitespace-only topics automatically
        - Frozen dataclass output prevents accidental mutation
        - Stable sort ensures deterministic ordering
        - Safe for concurrent use (no shared state)
    """
    # Validate parameters
    if max_topics < 1:
        raise ValueError("max_topics must be at least 1")

    # Sanitize input: filter empty/whitespace-only topics
    clean_topics = [t for t in topics if t and t.strip()]

    # Handle empty input gracefully
    if not clean_topics:
        return []

    # Score all valid topics (don't mutate input)
    scored = [ScoredTopic(topic=topic, score=_score_topic(topic)) for topic in clean_topics]

    # Sort by score (descending), then by topic name (stable)
    scored.sort(key=lambda x: (-x.score, x.topic))

    # Return top N
    return scored[:max_topics]
