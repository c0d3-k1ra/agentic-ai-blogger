"""
Tests for Topic Scout agent.

This test suite verifies:
- Basic topic generation functionality
- Deterministic behavior
- Input validation
- Output quality (no duplicates, no empty strings)
- Keyword expansion for multi-word seeds
- Whitespace normalization
"""

import pytest

from src.agents.topic_scout import TOPIC_TEMPLATES, generate_topics


class TestBasicGeneration:
    """Test basic topic generation functionality."""

    def test_basic_topic_generation(self):
        """Test that topics are generated from a simple seed."""
        topics = generate_topics("Python", max_topics=10)

        assert isinstance(topics, list)
        assert len(topics) > 0
        assert len(topics) <= 10
        assert all(isinstance(topic, str) for topic in topics)

    def test_returns_list_of_strings(self):
        """Test that output is always a list of strings."""
        topics = generate_topics("JavaScript", max_topics=5)

        assert isinstance(topics, list)
        for topic in topics:
            assert isinstance(topic, str)
            assert len(topic) > 0

    def test_max_topics_respected(self):
        """Test that output length never exceeds max_topics."""
        for max_val in [1, 5, 10, 20, 50]:
            topics = generate_topics("Python", max_topics=max_val)
            assert len(topics) <= max_val

    def test_generates_at_least_some_topics(self):
        """Test that we always generate at least one topic."""
        topics = generate_topics("Test", max_topics=1)
        assert len(topics) >= 1

    def test_different_seeds_produce_different_topics(self):
        """Test that different seeds produce different results."""
        python_topics = generate_topics("Python", max_topics=10)
        rust_topics = generate_topics("Rust", max_topics=10)

        # Topics should be different (at least most of them)
        assert python_topics != rust_topics
        assert any("Python" in t for t in python_topics)
        assert any("Rust" in t for t in rust_topics)


class TestDeterminism:
    """Test deterministic behavior."""

    def test_deterministic_output(self):
        """Test that same input always produces same output."""
        topics1 = generate_topics("Python Async", max_topics=20)
        topics2 = generate_topics("Python Async", max_topics=20)

        assert topics1 == topics2
        assert len(topics1) == len(topics2)

    def test_stable_ordering(self):
        """Test that topic order is stable across runs."""
        topics1 = generate_topics("Machine Learning", max_topics=15)
        topics2 = generate_topics("Machine Learning", max_topics=15)

        # Not just equal, but in exact same order
        for i, (t1, t2) in enumerate(zip(topics1, topics2)):
            assert t1 == t2, f"Mismatch at position {i}: {t1} != {t2}"

    def test_deterministic_with_different_max_topics(self):
        """Test that longer list is consistent with shorter list."""
        topics_short = generate_topics("Docker", max_topics=5)
        topics_long = generate_topics("Docker", max_topics=10)

        # First 5 should be identical
        assert topics_long[:5] == topics_short


class TestInputValidation:
    """Test input validation and edge cases."""

    def test_empty_seed_raises(self):
        """Test that empty seed_topic raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            generate_topics("", max_topics=10)

    def test_whitespace_only_seed_raises(self):
        """Test that whitespace-only seed raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            generate_topics("   ", max_topics=10)

        with pytest.raises(ValueError, match="cannot be empty"):
            generate_topics("\t\n", max_topics=10)

    def test_max_topics_less_than_one_raises(self):
        """Test that max_topics < 1 raises ValueError."""
        with pytest.raises(ValueError, match="must be at least 1"):
            generate_topics("Python", max_topics=0)

        with pytest.raises(ValueError, match="must be at least 1"):
            generate_topics("Python", max_topics=-1)

        with pytest.raises(ValueError, match="must be at least 1"):
            generate_topics("Python", max_topics=-100)

    def test_max_topics_one_works(self):
        """Test that max_topics=1 is valid."""
        topics = generate_topics("Python", max_topics=1)
        assert len(topics) == 1

    def test_none_seed_raises(self):
        """Test that None seed raises appropriate error."""
        with pytest.raises((ValueError, AttributeError, TypeError)):
            generate_topics(None, max_topics=10)


class TestOutputQuality:
    """Test output characteristics and quality."""

    def test_no_duplicates(self):
        """Test that output contains no duplicate topics."""
        topics = generate_topics("Python", max_topics=50)

        # Convert to set and compare lengths
        assert len(topics) == len(set(topics))

    def test_no_empty_strings(self):
        """Test that no topic is an empty string."""
        topics = generate_topics("JavaScript", max_topics=30)

        for topic in topics:
            assert topic, "Found empty topic"
            assert topic.strip(), "Found whitespace-only topic"

    def test_all_strings_non_empty(self):
        """Test that all returned strings have content."""
        topics = generate_topics("Kubernetes", max_topics=25)

        for topic in topics:
            assert isinstance(topic, str)
            assert len(topic) > 0
            assert len(topic.strip()) > 0

    def test_topics_contain_seed_or_keywords(self):
        """Test that generated topics relate to the seed."""
        topics = generate_topics("Python", max_topics=10)

        # All topics should contain "Python" (single word seed)
        for topic in topics:
            assert "Python" in topic

    def test_topics_are_well_formed(self):
        """Test that topics look like article titles."""
        topics = generate_topics("React Hooks", max_topics=10)

        for topic in topics:
            # Should not start/end with whitespace
            assert topic == topic.strip()
            # Should have reasonable length
            assert len(topic) > 5  # At least some content
            # Should not have control characters
            assert "\n" not in topic
            assert "\t" not in topic


class TestKeywordExpansion:
    """Test keyword expansion for multi-word seeds."""

    def test_single_word_seed_no_expansion(self):
        """Test that single-word seeds don't expand to multiple keywords."""
        topics = generate_topics("Python", max_topics=20)

        # All should contain "Python" (no keyword variants)
        for topic in topics:
            assert "Python" in topic

    def test_multi_word_seed_creates_variations(self):
        """Test that multi-word seeds create keyword variations."""
        topics = generate_topics("Python Async", max_topics=30)

        # Should have topics with full phrase
        full_phrase_topics = [t for t in topics if "Python Async" in t]
        assert len(full_phrase_topics) > 0

        # Should have topics with just "Python"
        python_only = [t for t in topics if "Python" in t and "Async" not in t]
        assert len(python_only) > 0

        # Should have topics with just "Async"
        async_only = [t for t in topics if "Async" in t and "Python" not in t]
        assert len(async_only) > 0

    def test_keyword_expansion_increases_diversity(self):
        """Test that multi-word seeds produce more diverse topics."""
        single_topics = set(generate_topics("Python", max_topics=30))
        multi_topics = set(generate_topics("Python Async", max_topics=30))

        # Multi-word should have unique topics not in single-word
        unique_to_multi = multi_topics - single_topics
        assert len(unique_to_multi) > 0

    def test_three_word_seed_expansion(self):
        """Test expansion with three-word seed."""
        topics = generate_topics("Python Web Framework", max_topics=40)

        # Should have full phrase
        assert any("Python Web Framework" in t for t in topics)

        # Should have individual keywords
        assert any("Python" in t and "Web" not in t and "Framework" not in t for t in topics)
        assert any("Web" in t and "Python" not in t and "Framework" not in t for t in topics)
        assert any("Framework" in t and "Python" not in t and "Web" not in t for t in topics)


class TestWhitespaceNormalization:
    """Test whitespace handling and normalization."""

    def test_whitespace_normalized(self):
        """Test that topics have normalized whitespace."""
        topics = generate_topics("Python  Async", max_topics=10)

        for topic in topics:
            # No double spaces
            assert "  " not in topic
            # No leading/trailing whitespace
            assert topic == topic.strip()
            # No tabs or newlines
            assert "\t" not in topic
            assert "\n" not in topic

    def test_multiple_spaces_in_seed_normalized(self):
        """Test that multiple spaces in seed are normalized."""
        topics = generate_topics("Python    Async", max_topics=10)

        for topic in topics:
            assert "    " not in topic
            assert "  " not in topic

    def test_tabs_in_seed_normalized(self):
        """Test that tabs in seed are normalized."""
        topics = generate_topics("Python\tAsync", max_topics=10)

        for topic in topics:
            assert "\t" not in topic

    def test_mixed_whitespace_normalized(self):
        """Test that mixed whitespace is normalized."""
        topics = generate_topics("Python \t\n Async", max_topics=10)

        for topic in topics:
            # Should be normalized to single spaces
            assert topic == " ".join(topic.split())


class TestTemplates:
    """Test template-related functionality."""

    def test_templates_defined(self):
        """Test that TOPIC_TEMPLATES is defined and populated."""
        assert TOPIC_TEMPLATES is not None
        assert len(TOPIC_TEMPLATES) > 0
        assert all(isinstance(t, str) for t in TOPIC_TEMPLATES)

    def test_templates_contain_placeholder(self):
        """Test that all templates contain {topic} placeholder."""
        for template in TOPIC_TEMPLATES:
            assert "{topic}" in template, f"Template missing placeholder: {template}"

    def test_templates_produce_valid_topics(self):
        """Test that templates format correctly."""
        for template in TOPIC_TEMPLATES[:5]:  # Test first 5
            topic = template.format(topic="Python")
            assert isinstance(topic, str)
            assert len(topic) > 0
            assert "{topic}" not in topic  # Should be replaced


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_seed_topic(self):
        """Test handling of very long seed topics."""
        long_seed = "Python Async Programming with Multiple Advanced Concepts"
        topics = generate_topics(long_seed, max_topics=20)

        assert len(topics) > 0
        assert all(isinstance(t, str) for t in topics)

    def test_seed_with_special_characters(self):
        """Test seed topics with special characters."""
        topics = generate_topics("C++", max_topics=10)
        assert len(topics) > 0
        assert all("C++" in t for t in topics)

    def test_seed_with_numbers(self):
        """Test seed topics with numbers."""
        topics = generate_topics("Python 3.12", max_topics=10)
        assert len(topics) > 0

    def test_unicode_seed(self):
        """Test seed topics with unicode characters."""
        topics = generate_topics("Python 编程", max_topics=10)
        assert len(topics) > 0
        assert all(isinstance(t, str) for t in topics)

    def test_max_topics_larger_than_possible(self):
        """Test when max_topics exceeds possible unique topics."""
        # With our current templates and single word, we can generate
        # len(TOPIC_TEMPLATES) unique topics at most
        topics = generate_topics("Python", max_topics=1000)

        # Should not crash, should return what's possible
        assert len(topics) > 0
        assert len(topics) <= len(TOPIC_TEMPLATES)

    def test_seed_with_only_spaces_between_words(self):
        """Test seed with multiple space-separated words."""
        topics = generate_topics("Machine Learning AI", max_topics=20)

        assert len(topics) > 0
        # Should have expansions for each word
        assert any("Machine" in t and "Learning" not in t for t in topics)
        assert any("Learning" in t and "Machine" not in t for t in topics)


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""

    def test_typical_usage_pattern(self):
        """Test typical usage as would be used in production."""
        seed = "Python Async"
        topics = generate_topics(seed, max_topics=30)

        # Should produce reasonable results
        assert 10 <= len(topics) <= 30
        assert all(isinstance(t, str) for t in topics)
        assert len(set(topics)) == len(topics)  # No duplicates

    def test_batch_generation(self):
        """Test generating topics for multiple seeds."""
        seeds = ["Python", "JavaScript", "Rust", "Go"]

        for seed in seeds:
            topics = generate_topics(seed, max_topics=20)
            assert len(topics) > 0
            assert all(seed in t for t in topics)

    def test_progressive_expansion(self):
        """Test that increasing max_topics gives consistent prefix."""
        seed = "Docker Kubernetes"

        topics_10 = generate_topics(seed, max_topics=10)
        topics_20 = generate_topics(seed, max_topics=20)
        topics_30 = generate_topics(seed, max_topics=30)

        # First 10 should be same
        assert topics_20[:10] == topics_10
        assert topics_30[:10] == topics_10
        assert topics_30[:20] == topics_20
