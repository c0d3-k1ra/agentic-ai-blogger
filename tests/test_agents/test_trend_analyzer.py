"""
Tests for Trend Analyzer agent.

This test suite verifies:
- Basic scoring functionality
- Deterministic behavior
- Stable ordering
- Max topics parameter
- Empty and small input handling
- Score distribution and heuristics
- Input immutability
- Input sanitization
- Frozen dataclass behavior
"""

import pytest

from src.agents.trend_analyzer import (
    GENERIC_PHRASES,
    SPECIFICITY_KEYWORDS,
    STOPWORDS,
    ScoredTopic,
    analyze_trends,
)


class TestBasicScoring:
    """Test basic scoring functionality."""

    def test_basic_scoring(self):
        """Test that topics are scored and returned."""
        topics = ["Python Programming", "Advanced Python Techniques"]
        results = analyze_trends(topics, max_topics=5)

        assert len(results) == 2
        assert all(isinstance(r, ScoredTopic) for r in results)

    def test_returns_scored_topics(self):
        """Test that output contains ScoredTopic objects."""
        topics = ["Python", "Java", "Rust"]
        results = analyze_trends(topics, max_topics=3)

        for result in results:
            assert isinstance(result, ScoredTopic)
            assert isinstance(result.topic, str)
            assert isinstance(result.score, float)

    def test_score_is_float(self):
        """Test that scores are float type."""
        topics = ["Machine Learning"]
        results = analyze_trends(topics, max_topics=1)

        assert isinstance(results[0].score, float)
        assert results[0].score >= 0.0

    def test_different_topics_different_scores(self):
        """Test that different topics produce different scores."""
        topics = [
            "Advanced Python Performance Optimization",  # High quality
            "Python",  # Too short
            "Introduction to Python",  # Generic
        ]
        results = analyze_trends(topics, max_topics=3)

        # Scores should vary
        scores = [r.score for r in results]
        assert len(set(scores)) > 1  # At least some different scores

    def test_all_scores_non_negative(self):
        """Test that all scores are non-negative."""
        topics = ["A", "Test", "Python", "Long Topic Title Here"]
        results = analyze_trends(topics, max_topics=10)

        for result in results:
            assert result.score >= 0.0


class TestDeterminism:
    """Test deterministic behavior."""

    def test_deterministic_output(self):
        """Test that same input produces same output."""
        topics = ["Python", "Java", "Rust", "Go", "JavaScript"]

        results1 = analyze_trends(topics, max_topics=3)
        results2 = analyze_trends(topics, max_topics=3)

        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert r1.topic == r2.topic
            assert r1.score == r2.score

    def test_same_scores_across_runs(self):
        """Test that scores are consistent across multiple runs."""
        topic = "Advanced Python Performance Optimization"

        scores = []
        for _ in range(5):
            results = analyze_trends([topic], max_topics=1)
            scores.append(results[0].score)

        # All scores should be identical
        assert len(set(scores)) == 1


class TestStableOrdering:
    """Test ordering stability."""

    def test_stable_ordering_by_score(self):
        """Test that topics are sorted by descending score."""
        topics = [
            "Introduction to Python",  # Generic, should score lower
            "Advanced Python Performance Optimization",  # Should score higher
            "Python",  # Too short
        ]

        results = analyze_trends(topics, max_topics=3)

        # Verify descending order
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_stable_secondary_sort_by_name(self):
        """Test that equal scores are sorted alphabetically."""
        # Create topics that should have similar scores
        topics = ["Python Guide", "Java Guide", "Rust Guide"]

        results = analyze_trends(topics, max_topics=3)

        # Extract topics with similar scores (within 0.01)
        if abs(results[0].score - results[1].score) < 0.01:
            # Should be alphabetically ordered
            assert results[0].topic < results[1].topic or results[0].score > results[1].score


class TestMaxTopics:
    """Test max_topics parameter."""

    def test_max_topics_respected(self):
        """Test that output never exceeds max_topics."""
        topics = ["Topic " + str(i) for i in range(20)]

        for max_val in [1, 3, 5, 10]:
            results = analyze_trends(topics, max_topics=max_val)
            assert len(results) <= max_val

    def test_max_topics_less_than_input(self):
        """Test max_topics smaller than input size."""
        topics = ["Python", "Java", "Rust", "Go", "JavaScript"]
        results = analyze_trends(topics, max_topics=2)

        assert len(results) == 2

    def test_max_topics_more_than_input(self):
        """Test max_topics larger than input size."""
        topics = ["Python", "Java"]
        results = analyze_trends(topics, max_topics=10)

        assert len(results) == 2  # Only returns available topics

    def test_max_topics_validation(self):
        """Test that max_topics < 1 raises ValueError."""
        with pytest.raises(ValueError, match="must be at least 1"):
            analyze_trends(["Python"], max_topics=0)

        with pytest.raises(ValueError, match="must be at least 1"):
            analyze_trends(["Python"], max_topics=-1)

    def test_max_topics_one(self):
        """Test that max_topics=1 works."""
        topics = ["Python", "Java", "Rust"]
        results = analyze_trends(topics, max_topics=1)

        assert len(results) == 1


class TestEmptyAndSmallInputs:
    """Test edge cases with empty and small inputs."""

    def test_empty_input_returns_empty(self):
        """Test that empty list returns empty list."""
        results = analyze_trends([], max_topics=5)
        assert results == []

    def test_single_topic(self):
        """Test handling of single topic."""
        results = analyze_trends(["Python"], max_topics=5)

        assert len(results) == 1
        assert results[0].topic == "Python"
        assert isinstance(results[0].score, float)

    def test_all_empty_topics_returns_empty(self):
        """Test that all-empty input returns empty list."""
        topics = ["", "  ", "\t", "\n"]
        results = analyze_trends(topics, max_topics=5)

        assert results == []


class TestScoreDistribution:
    """Test scoring heuristics work as expected."""

    def test_length_score_preference(self):
        """Test that optimal length topics score higher."""
        # Optimal length (40-80 chars) should score higher than extreme lengths
        optimal = "Advanced Python Programming Design Patterns"  # ~45 chars
        too_short = "Python"  # ~6 chars
        too_long = "A" * 120  # 120 chars

        results = analyze_trends([optimal, too_short, too_long], max_topics=3)

        optimal_score = next(r.score for r in results if r.topic == optimal)
        short_score = next(r.score for r in results if r.topic == too_short)
        long_score = next(r.score for r in results if r.topic == too_long)

        assert optimal_score > short_score
        assert optimal_score > long_score

    def test_keyword_richness_matters(self):
        """Test that keyword-rich topics score higher."""
        rich = "Python Programming Tutorial"  # All meaningful words
        poor = "Introduction to the Python"  # More stopwords

        results = analyze_trends([rich, poor], max_topics=2)

        rich_score = next(r.score for r in results if r.topic == rich)
        poor_score = next(r.score for r in results if r.topic == poor)

        # Rich should score higher (keyword richness)
        assert rich_score > poor_score

    def test_specificity_bonus_applied(self):
        """Test that specific keywords increase score."""
        specific = "Advanced Python Performance Optimization"  # Has specific keywords
        generic_topic = "Python Programming Language"  # No specific keywords

        results = analyze_trends([specific, generic_topic], max_topics=2)

        specific_score = next(r.score for r in results if r.topic == specific)
        generic_score = next(r.score for r in results if r.topic == generic_topic)

        # Specific should score higher due to bonus
        assert specific_score > generic_score

    def test_generic_penalty_applied(self):
        """Test that generic phrases decrease score."""
        generic = "Introduction to Python Programming"  # Has "introduction to"
        non_generic = "Python Programming Concepts"  # No generic phrases

        results = analyze_trends([generic, non_generic], max_topics=2)

        generic_score = next(r.score for r in results if r.topic == generic)
        non_generic_score = next(r.score for r in results if r.topic == non_generic)

        # Generic should score lower due to penalty
        assert non_generic_score > generic_score


class TestInputMutation:
    """Test that input is not mutated."""

    def test_no_mutation_of_input_list(self):
        """Test that input list is not modified."""
        topics = ["Python", "Java", "Rust"]
        original = topics.copy()

        analyze_trends(topics, max_topics=2)

        assert topics == original

    def test_input_topics_unchanged(self):
        """Test that individual topic strings are unchanged."""
        topic = "Python Programming"
        topics = [topic]

        analyze_trends(topics, max_topics=1)

        assert topics[0] == topic
        assert topics[0] is topic  # Same object reference


class TestInputSanitization:
    """Test input cleaning and validation."""

    def test_filters_empty_strings(self):
        """Test that empty strings are filtered out."""
        topics = ["Python", "", "Java", ""]
        results = analyze_trends(topics, max_topics=5)

        assert len(results) == 2
        assert all(r.topic in ["Python", "Java"] for r in results)

    def test_filters_whitespace_only(self):
        """Test that whitespace-only topics are filtered."""
        topics = ["Python", "   ", "\t\n", "Java"]
        results = analyze_trends(topics, max_topics=5)

        assert len(results) == 2
        topics_returned = [r.topic for r in results]
        assert "Python" in topics_returned
        assert "Java" in topics_returned

    def test_handles_all_invalid_input(self):
        """Test that all-invalid input returns empty list."""
        topics = ["", "  ", "\t", "\n", "   \t\n   "]
        results = analyze_trends(topics, max_topics=5)

        assert results == []

    def test_mixed_valid_invalid_input(self):
        """Test mixture of valid and invalid topics."""
        topics = ["", "Python", "  ", "Java", "\t"]
        results = analyze_trends(topics, max_topics=10)

        assert len(results) == 2


class TestScoredTopicImmutability:
    """Test frozen dataclass behavior."""

    def test_scored_topic_is_frozen(self):
        """Test that ScoredTopic cannot be modified."""
        st = ScoredTopic(topic="Python", score=0.5)

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            st.score = 0.9

        with pytest.raises(Exception):
            st.topic = "Java"

    def test_scored_topic_is_hashable(self):
        """Test that ScoredTopic can be hashed."""
        st = ScoredTopic(topic="Python", score=0.5)

        # Should not raise
        hash(st)

        # Can be added to set
        topic_set = {st}
        assert st in topic_set

    def test_scored_topic_equality(self):
        """Test ScoredTopic equality comparison."""
        st1 = ScoredTopic(topic="Python", score=0.5)
        st2 = ScoredTopic(topic="Python", score=0.5)
        st3 = ScoredTopic(topic="Java", score=0.5)

        assert st1 == st2
        assert st1 != st3


class TestScoringComponents:
    """Test individual scoring functions and constants."""

    def test_stopwords_defined(self):
        """Test that STOPWORDS constant is populated."""
        assert len(STOPWORDS) > 0
        assert "the" in STOPWORDS
        assert "a" in STOPWORDS
        assert "is" in STOPWORDS

    def test_specificity_keywords_defined(self):
        """Test that SPECIFICITY_KEYWORDS is populated."""
        assert len(SPECIFICITY_KEYWORDS) > 0
        assert "advanced" in SPECIFICITY_KEYWORDS
        assert "performance" in SPECIFICITY_KEYWORDS
        assert "guide" in SPECIFICITY_KEYWORDS

    def test_generic_phrases_defined(self):
        """Test that GENERIC_PHRASES is populated."""
        assert len(GENERIC_PHRASES) > 0
        assert "introduction to" in GENERIC_PHRASES
        assert "getting started" in GENERIC_PHRASES

    def test_constants_are_sets(self):
        """Test that constants are set type for O(1) lookup."""
        assert isinstance(STOPWORDS, set)
        assert isinstance(SPECIFICITY_KEYWORDS, set)
        assert isinstance(GENERIC_PHRASES, set)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_topic(self):
        """Test handling of extremely long topics."""
        long_topic = "A" * 200
        results = analyze_trends([long_topic], max_topics=1)

        assert len(results) == 1
        assert results[0].score >= 0.0

    def test_special_characters_in_topic(self):
        """Test topics with special characters."""
        topics = ["C++ Programming", "Node.js Guide", "Rust & Go"]
        results = analyze_trends(topics, max_topics=3)

        assert len(results) == 3
        assert all(r.score >= 0.0 for r in results)

    def test_unicode_topics(self):
        """Test topics with unicode characters."""
        topics = ["Python 编程", "Rust プログラミング"]
        results = analyze_trends(topics, max_topics=2)

        assert len(results) == 2

    def test_numbers_in_topics(self):
        """Test topics containing numbers."""
        topics = ["Python 3.12 Guide", "Web3 Development"]
        results = analyze_trends(topics, max_topics=2)

        assert len(results) == 2

    def test_case_insensitive_matching(self):
        """Test that keyword matching is case-insensitive."""
        lower = "advanced python techniques"
        upper = "ADVANCED PYTHON TECHNIQUES"
        mixed = "Advanced Python Techniques"

        results = analyze_trends([lower, upper, mixed], max_topics=3)

        # All should have same score (case-insensitive)
        scores = [r.score for r in results]
        assert len(set(scores)) == 1  # All identical


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""

    def test_typical_usage_pattern(self):
        """Test typical usage as would be used in production."""
        # Simulate Topic Scout output
        topics = [
            "Introduction to Python",
            "Advanced Python Performance Optimization",
            "Python Programming",
            "Getting Started with Python",
            "Python Best Practices for Production",
            "Python Design Patterns",
        ]

        results = analyze_trends(topics, max_topics=3)

        # Should return 3 topics
        assert len(results) == 3

        # Specific topics should rank higher than generic
        top_topics = [r.topic for r in results]
        assert "Advanced Python Performance Optimization" in top_topics

    def test_score_ordering_makes_sense(self):
        """Test that score ordering aligns with intuition."""
        topics = [
            "Introduction to Python",  # Generic
            "Python",  # Too short
            "Advanced Python Performance Optimization Techniques",  # Specific
            "Python Programming Best Practices",  # Good
        ]

        results = analyze_trends(topics, max_topics=4)

        # Advanced/specific should be near top
        top_score = results[0].score
        bottom_score = results[-1].score
        assert top_score > bottom_score

    def test_batch_scoring_consistency(self):
        """Test that scoring multiple batches is consistent."""
        all_topics = ["Topic " + str(i) for i in range(20)]

        # Score all at once
        all_results = analyze_trends(all_topics, max_topics=20)

        # Score in batches
        batch1 = analyze_trends(all_topics[:10], max_topics=10)
        batch2 = analyze_trends(all_topics[10:], max_topics=10)

        # Verify consistency: same topics should have same scores
        # Check first batch
        for topic in all_topics[:10]:
            all_score = next(r.score for r in all_results if r.topic == topic)
            batch_score = next(r.score for r in batch1 if r.topic == topic)
            assert all_score == batch_score

        # Check second batch
        for topic in all_topics[10:]:
            all_score = next(r.score for r in all_results if r.topic == topic)
            batch_score = next(r.score for r in batch2 if r.topic == topic)
            assert all_score == batch_score


class TestScoreCorrectness:
    """Test that scoring logic is implemented correctly."""

    def test_base_score_calculation(self):
        """Test that base score is properly calculated."""
        # Topic with optimal length and high keyword richness
        topic = "Python Programming Design Patterns Tutorial"  # ~45 chars

        results = analyze_trends([topic], max_topics=1)
        score = results[0].score

        # Should have decent base score (length + keywords)
        assert score > 0.3  # At least some base score

    def test_bonus_not_double_weighted(self):
        """Test that specificity bonus is added, not multiplied."""
        specific = "Advanced Performance Optimization Tutorial"
        results = analyze_trends([specific], max_topics=1)

        # Should have bonus from multiple specific keywords
        # Score should be > base (0.6) due to bonus
        assert results[0].score > 0.6

    def test_penalty_full_impact(self):
        """Test that generic penalty has proper effect."""
        generic = "Introduction to Python Programming"
        results = analyze_trends([generic], max_topics=1)

        # Should have penalty applied
        # Generic phrase should reduce score significantly
        assert results[0].score < 0.5  # Penalty should pull down score
