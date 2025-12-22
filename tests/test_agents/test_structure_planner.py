"""
Tests for Structure Planner agent.

This test suite verifies:
- Basic outline structure
- Deterministic behavior
- Max sections handling
- Section quality (no duplicates, no empty titles)
- Input validation
- True immutability (tuples)
- Title normalization (no adjacent duplicates)
- Intro and conclusion guarantees
"""

import pytest

from src.agents.structure_planner import (
    SECTION_TEMPLATES,
    Outline,
    Section,
    _determine_sections,
    _generate_section,
    _normalize_title,
    generate_outline,
)


class TestBasicStructure:
    """Test basic outline structure generation."""

    def test_basic_outline_structure(self):
        """Test that outline is generated with expected structure."""
        outline = generate_outline("Python Programming")

        assert isinstance(outline, Outline)
        assert isinstance(outline.topic, str)
        assert isinstance(outline.sections, tuple)
        assert len(outline.sections) > 0

    def test_returns_outline_object(self):
        """Test that function returns Outline dataclass."""
        result = generate_outline("Machine Learning")

        assert isinstance(result, Outline)
        assert hasattr(result, "topic")
        assert hasattr(result, "sections")

    def test_sections_have_subsections(self):
        """Test that each section contains subsections."""
        outline = generate_outline("Python")

        for section in outline.sections:
            assert isinstance(section, Section)
            assert isinstance(section.title, str)
            assert isinstance(section.subsections, tuple)
            assert len(section.subsections) > 0

    def test_section_count_reasonable(self):
        """Test that section count is reasonable."""
        outline = generate_outline("Python", max_sections=6)

        assert 2 <= len(outline.sections) <= 6


class TestDeterminism:
    """Test deterministic behavior."""

    def test_determinism(self):
        """Test that same input produces same output."""
        topic = "Python Async Programming"

        outline1 = generate_outline(topic)
        outline2 = generate_outline(topic)

        assert outline1.topic == outline2.topic
        assert len(outline1.sections) == len(outline2.sections)

        for s1, s2 in zip(outline1.sections, outline2.sections):
            assert s1.title == s2.title
            assert s1.subsections == s2.subsections

    def test_same_topic_same_outline(self):
        """Test determinism across multiple runs."""
        topic = "Advanced Python Techniques"

        outlines = [generate_outline(topic) for _ in range(5)]

        # All should be identical
        first = outlines[0]
        for outline in outlines[1:]:
            assert outline.topic == first.topic
            assert len(outline.sections) == len(first.sections)

            for s1, s2 in zip(outline.sections, first.sections):
                assert s1.title == s2.title
                assert s1.subsections == s2.subsections

    def test_ordering_stable(self):
        """Test that section ordering is stable."""
        outline1 = generate_outline("Python")
        outline2 = generate_outline("Python")

        titles1 = [s.title for s in outline1.sections]
        titles2 = [s.title for s in outline2.sections]

        assert titles1 == titles2


class TestMaxSections:
    """Test max_sections parameter."""

    def test_max_sections_respected(self):
        """Test that output never exceeds max_sections."""
        for max_val in [2, 3, 4, 5, 6, 10]:
            outline = generate_outline("Python", max_sections=max_val)
            assert len(outline.sections) <= max_val

    def test_max_sections_minimum(self):
        """Test that max_sections=2 works (intro + conclusion)."""
        outline = generate_outline("Python", max_sections=2)

        assert len(outline.sections) == 2
        assert "Introduction" in outline.sections[0].title
        assert "Conclusion" in outline.sections[1].title

    def test_max_sections_caps_output(self):
        """Test that max_sections limits middle sections."""
        outline_small = generate_outline("Python", max_sections=3)
        outline_large = generate_outline("Python", max_sections=6)

        assert len(outline_small.sections) == 3
        assert len(outline_large.sections) == 6

    def test_max_sections_validation(self):
        """Test that max_sections < 2 raises ValueError."""
        with pytest.raises(ValueError, match="at least 2"):
            generate_outline("Python", max_sections=1)

        with pytest.raises(ValueError, match="at least 2"):
            generate_outline("Python", max_sections=0)

        with pytest.raises(ValueError, match="at least 2"):
            generate_outline("Python", max_sections=-1)


class TestSectionQuality:
    """Test section quality constraints."""

    def test_no_duplicate_sections(self):
        """Test that no duplicate section titles exist."""
        outline = generate_outline("Python Programming")

        titles = [s.title for s in outline.sections]
        assert len(titles) == len(set(titles))

    def test_no_empty_titles(self):
        """Test that no section has empty title."""
        outline = generate_outline("Python")

        for section in outline.sections:
            assert section.title
            assert section.title.strip()

    def test_no_empty_subsections(self):
        """Test that no subsection has empty title."""
        outline = generate_outline("Python")

        for section in outline.sections:
            for subsection in section.subsections:
                assert subsection
                assert subsection.strip()

    def test_logical_section_order(self):
        """Test that sections follow logical order."""
        outline = generate_outline("Python", max_sections=6)

        titles = [s.title for s in outline.sections]

        # First should be introduction
        assert "Introduction" in titles[0]

        # Last should be conclusion
        assert "Conclusion" in titles[-1]


class TestInputValidation:
    """Test input validation."""

    def test_empty_topic_raises(self):
        """Test that empty topic raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            generate_outline("")

    def test_whitespace_topic_raises(self):
        """Test that whitespace-only topic raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            generate_outline("   ")

        with pytest.raises(ValueError, match="cannot be empty"):
            generate_outline("\t\n")

    def test_topic_preserved(self):
        """Test that topic is preserved in output."""
        topic = "Python Async Programming"
        outline = generate_outline(topic)

        assert outline.topic == topic

    def test_topic_whitespace_stripped(self):
        """Test that leading/trailing whitespace is stripped."""
        outline = generate_outline("  Python  ")

        assert outline.topic == "Python"
        assert outline.topic == outline.topic.strip()


class TestImmutability:
    """Test true immutability with tuples."""

    def test_outline_is_frozen(self):
        """Test that Outline is frozen dataclass."""
        outline = generate_outline("Python")

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            outline.topic = "Java"

        with pytest.raises(Exception):
            outline.sections = ()

    def test_section_is_frozen(self):
        """Test that Section is frozen dataclass."""
        outline = generate_outline("Python")
        section = outline.sections[0]

        with pytest.raises(Exception):
            section.title = "New Title"

        with pytest.raises(Exception):
            section.subsections = ()

    def test_sections_is_tuple(self):
        """Test that sections is a tuple, not list."""
        outline = generate_outline("Python")

        assert isinstance(outline.sections, tuple)
        assert not isinstance(outline.sections, list)

    def test_subsections_is_tuple(self):
        """Test that subsections is a tuple, not list."""
        outline = generate_outline("Python")

        for section in outline.sections:
            assert isinstance(section.subsections, tuple)
            assert not isinstance(section.subsections, list)

    def test_cannot_mutate_sections(self):
        """Test that sections tuple cannot be modified."""
        outline = generate_outline("Python")

        with pytest.raises(Exception):  # TypeError or AttributeError
            outline.sections[0] = Section("New", ("sub",))

        with pytest.raises(Exception):
            outline.sections.append(Section("New", ("sub",)))

    def test_cannot_mutate_subsections(self):
        """Test that subsections tuple cannot be modified."""
        outline = generate_outline("Python")
        section = outline.sections[0]

        with pytest.raises(Exception):
            section.subsections[0] = "New Subsection"

        with pytest.raises(Exception):
            section.subsections.append("New Subsection")

    def test_outline_is_hashable(self):
        """Test that Outline can be hashed (frozen + tuples)."""
        outline = generate_outline("Python")

        # Should not raise
        hash(outline)

        # Can be added to set
        outline_set = {outline}
        assert outline in outline_set

    def test_section_is_hashable(self):
        """Test that Section can be hashed."""
        outline = generate_outline("Python")
        section = outline.sections[0]

        # Should not raise
        hash(section)

        # Can be added to set
        section_set = {section}
        assert section in section_set


class TestTitleNormalization:
    """Test title normalization (deduplication)."""

    def test_removes_duplicate_adjacent_words(self):
        """Test that _normalize_title removes adjacent duplicates."""
        assert _normalize_title("Advanced Advanced Python") == "Advanced Python"
        assert _normalize_title("The the Guide") == "The Guide"
        assert _normalize_title("Python Python Python") == "Python"

    def test_case_insensitive_deduplication(self):
        """Test that deduplication is case-insensitive."""
        assert _normalize_title("Advanced advanced Python") == "Advanced Python"
        assert _normalize_title("THE the Guide") == "THE Guide"
        assert _normalize_title("Python PYTHON python") == "Python"

    def test_preserves_non_adjacent_duplicates(self):
        """Test that non-adjacent duplicates are preserved."""
        assert _normalize_title("Introduction to Introduction") == "Introduction to Introduction"
        assert _normalize_title("Python is Python") == "Python is Python"

    def test_handles_empty_strings(self):
        """Test that empty string handling works."""
        assert _normalize_title("") == ""
        assert _normalize_title("   ") == ""

    def test_handles_single_word(self):
        """Test that single word is unchanged."""
        assert _normalize_title("Python") == "Python"
        assert _normalize_title("Advanced") == "Advanced"

    def test_no_duplicate_words_in_generated_titles(self):
        """Test that generated titles have no adjacent duplicates."""
        # This tests the integration: "Advanced Python" topic with "Advanced" template
        outline = generate_outline("Advanced Python Programming")

        for section in outline.sections:
            title = section.title
            words = title.split()

            # Check no adjacent duplicates (case-insensitive)
            for i in range(len(words) - 1):
                assert (
                    words[i].lower() != words[i + 1].lower()
                ), f"Adjacent duplicate in title: {title}"


class TestIntroAndConclusion:
    """Test intro and conclusion guarantees."""

    def test_always_has_introduction_first(self):
        """Test that introduction is always first section."""
        for max_sections in [2, 3, 4, 5, 6]:
            outline = generate_outline("Python", max_sections=max_sections)
            assert "Introduction" in outline.sections[0].title

    def test_always_has_conclusion_last(self):
        """Test that conclusion is always last section."""
        for max_sections in [2, 3, 4, 5, 6]:
            outline = generate_outline("Python", max_sections=max_sections)
            assert "Conclusion" in outline.sections[-1].title

    def test_max_sections_two_gives_intro_conclusion(self):
        """Test that max_sections=2 gives only intro and conclusion."""
        outline = generate_outline("Python", max_sections=2)

        assert len(outline.sections) == 2
        assert "Introduction" in outline.sections[0].title
        assert "Conclusion" in outline.sections[1].title

    def test_conclusion_never_missing(self):
        """Test that conclusion is never omitted."""
        for max_sections in range(2, 10):
            outline = generate_outline("Python", max_sections=max_sections)
            titles = [s.title for s in outline.sections]
            conclusion_titles = [t for t in titles if "Conclusion" in t]
            assert len(conclusion_titles) == 1

    def test_introduction_never_missing(self):
        """Test that introduction is never omitted."""
        for max_sections in range(2, 10):
            outline = generate_outline("Python", max_sections=max_sections)
            titles = [s.title for s in outline.sections]
            intro_titles = [t for t in titles if "Introduction" in t]
            assert len(intro_titles) == 1


class TestSectionSelection:
    """Test smart section selection logic."""

    def test_advanced_topic_gets_advanced_section(self):
        """Test that 'advanced' in topic triggers advanced section."""
        outline = generate_outline("Advanced Python Patterns", max_sections=5)

        titles = [s.title for s in outline.sections]
        # Should include "Advanced Techniques"
        assert any("Advanced Techniques" in t for t in titles)

    def test_basic_topic_gets_practical_section(self):
        """Test that basic topics get practical section."""
        outline = generate_outline("Python Basics", max_sections=5)

        titles = [s.title for s in outline.sections]
        # Should include "Practical Implementation"
        assert any("Practical" in t for t in titles)

    def test_expert_keyword_triggers_advanced(self):
        """Test that 'expert' keyword triggers advanced section."""
        outline = generate_outline("Expert Python Techniques", max_sections=5)

        titles = [s.title for s in outline.sections]
        assert any("Advanced Techniques" in t for t in titles)

    def test_deep_keyword_triggers_advanced(self):
        """Test that 'deep' keyword triggers advanced section."""
        outline = generate_outline("Deep Dive into Python", max_sections=5)

        titles = [s.title for s in outline.sections]
        assert any("Advanced Techniques" in t for t in titles)


class TestSubsections:
    """Test subsection generation."""

    def test_all_sections_have_subsections(self):
        """Test that every section has subsections."""
        outline = generate_outline("Python")

        for section in outline.sections:
            assert len(section.subsections) > 0

    def test_introduction_first_subsection_has_topic(self):
        """Test that intro first subsection contains topic."""
        topic = "Python Async Programming"
        outline = generate_outline(topic)

        intro_section = outline.sections[0]
        first_subsection = intro_section.subsections[0]

        assert topic in first_subsection

    def test_introduction_other_subsections_generic(self):
        """Test that intro other subsections are generic."""
        topic = "Python Async Programming"
        outline = generate_outline(topic)

        intro_section = outline.sections[0]

        # First subsection has topic
        assert topic in intro_section.subsections[0]

        # Others should NOT have full topic
        for subsection in intro_section.subsections[1:]:
            # Generic subsections like "Why It Matters"
            assert subsection in ["Why It Matters", "Who Should Read This", "Article Overview"]

    def test_other_sections_subsections_generic(self):
        """Test that non-intro sections have generic subsections."""
        outline = generate_outline("Python Programming")

        # Skip introduction (index 0)
        for section in outline.sections[1:]:
            for subsection in section.subsections:
                # Should be from templates, not topic-specific
                assert "Python Programming" not in subsection


class TestInputMutation:
    """Test that input is not mutated."""

    def test_topic_not_mutated(self):
        """Test that input topic string is not mutated."""
        topic = "Python Programming"
        original = topic

        generate_outline(topic)

        assert topic == original
        assert topic is original  # Same object


class TestHelperFunctions:
    """Test internal helper functions."""

    def test_determine_sections_basic(self):
        """Test _determine_sections with basic topic."""
        sections = _determine_sections("Python", 3)

        assert sections[0] == "introduction"
        assert sections[-1] == "conclusion"
        assert len(sections) == 3

    def test_determine_sections_advanced_topic(self):
        """Test _determine_sections with advanced keyword."""
        sections = _determine_sections("Advanced Python", 5)

        assert "introduction" in sections
        assert "conclusion" in sections
        assert "advanced" in sections

    def test_generate_section_creates_section(self):
        """Test _generate_section creates Section object."""
        section = _generate_section("fundamentals", "Python")

        assert isinstance(section, Section)
        assert isinstance(section.title, str)
        assert isinstance(section.subsections, tuple)

    def test_section_templates_defined(self):
        """Test that SECTION_TEMPLATES is properly defined."""
        assert isinstance(SECTION_TEMPLATES, dict)
        assert len(SECTION_TEMPLATES) > 0

        required_sections = ["introduction", "fundamentals", "conclusion"]
        for section_type in required_sections:
            assert section_type in SECTION_TEMPLATES
            assert "title" in SECTION_TEMPLATES[section_type]
            assert "subsections" in SECTION_TEMPLATES[section_type]


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""

    def test_typical_python_topic(self):
        """Test typical Python programming topic."""
        outline = generate_outline("Python Async Programming")

        assert outline.topic == "Python Async Programming"
        assert len(outline.sections) >= 3
        assert "Introduction" in outline.sections[0].title
        assert "Conclusion" in outline.sections[-1].title

    def test_advanced_topic_scenario(self):
        """Test advanced technical topic."""
        outline = generate_outline("Advanced Python Design Patterns", max_sections=6)

        titles = [s.title for s in outline.sections]

        # Should have advanced section
        assert any("Advanced" in t for t in titles)

        # Should have all core sections
        assert "Introduction" in titles[0]
        assert "Conclusion" in titles[-1]

    def test_minimal_outline(self):
        """Test minimal outline (2 sections)."""
        outline = generate_outline("Python", max_sections=2)

        assert len(outline.sections) == 2
        assert "Introduction" in outline.sections[0].title
        assert "Conclusion" in outline.sections[1].title

    def test_maximal_outline(self):
        """Test maximal outline."""
        outline = generate_outline("Python", max_sections=10)

        # Should have intro, conclusion, and several middle sections
        assert len(outline.sections) >= 4
        assert len(outline.sections) <= 10


class TestEdgeCases:
    """Test edge cases."""

    def test_very_long_topic(self):
        """Test handling of very long topic names."""
        long_topic = "A" * 200
        outline = generate_outline(long_topic)

        assert outline.topic == long_topic
        assert len(outline.sections) > 0

    def test_special_characters_in_topic(self):
        """Test topics with special characters."""
        topic = "C++ Modern Features & Best Practices"
        outline = generate_outline(topic)

        assert outline.topic == topic
        assert len(outline.sections) > 0

    def test_unicode_topic(self):
        """Test topics with unicode characters."""
        topic = "Python 编程指南"
        outline = generate_outline(topic)

        assert outline.topic == topic
        assert len(outline.sections) > 0

    def test_numbers_in_topic(self):
        """Test topics with numbers."""
        topic = "Python 3.12 New Features"
        outline = generate_outline(topic)

        assert outline.topic == topic
        assert len(outline.sections) > 0
