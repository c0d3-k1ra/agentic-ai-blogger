"""Tests for the revision agent.

Tests cover:
- Article revision based on feedback
- Content extraction and parsing
- Word counting
- Input validation
- Error handling
- Immutability
"""

import pytest

from src.agents.revision import (
    RevisedArticle,
    _count_words,
    _extract_changes_summary,
    _extract_revised_content,
    revise_article,
)


class TestHelperFunctions:
    """Tests for internal helper functions."""

    def test_count_words_normal(self):
        """Count words in normal text."""
        assert _count_words("Hello world") == 2
        assert _count_words("One two three four") == 4

    def test_count_words_empty(self):
        """Empty string returns 0."""
        assert _count_words("") == 0
        assert _count_words("   ") == 0

    def test_count_words_markdown(self):
        """Count words in markdown content."""
        markdown = "# Title\n\nThis is content with **bold** text."
        assert _count_words(markdown) == 8

    def test_extract_changes_summary_with_changes_marker(self):
        """Extract from 'Changes:' line."""
        response = "Changes: Updated introduction and added examples\nRevised Content:\n..."
        summary = _extract_changes_summary(response)

        assert summary == "Updated introduction and added examples"

    def test_extract_changes_summary_with_summary_marker(self):
        """Extract from 'Summary:' line."""
        response = "Summary: Fixed typos and improved clarity\nContent:\n..."
        summary = _extract_changes_summary(response)

        assert summary == "Fixed typos and improved clarity"

    def test_extract_changes_summary_no_marker(self):
        """Default message when no marker found."""
        response = "Just some content without markers"
        summary = _extract_changes_summary(response)

        assert summary == "Applied user feedback"

    def test_extract_revised_content_with_marker(self):
        """Extract content after 'Revised Content:' marker."""
        response = "Changes: Made edits\nRevised Content:\n# New Article\n\nNew content here"
        content = _extract_revised_content(response, "# Old")

        assert content == "# New Article\n\nNew content here"

    def test_extract_revised_content_alternative_markers(self):
        """Extract with different content markers."""
        response1 = "Changes: X\nRevised Article:\n# Content"
        assert _extract_revised_content(response1, "# Old").startswith("# Content")

        response2 = "Changes: Y\nUpdated Content:\n# Content"
        assert _extract_revised_content(response2, "# Old").startswith("# Content")

    def test_extract_revised_content_markdown_detection(self):
        """Detect if response IS the content (starts with #)."""
        response = "# My Article\n\nThis is the full content"
        content = _extract_revised_content(response, "# Old")

        assert content == response.strip()

    def test_extract_revised_content_fallback(self):
        """Fallback to original if extraction fails."""
        response = "Short text"
        original = "# Original Content"
        content = _extract_revised_content(response, original)

        assert content == original


class TestReviseArticle:
    """Tests for the main revise_article function."""

    @pytest.mark.asyncio
    async def test_revise_article_basic(self):
        """Test basic revision with mocked LLM."""
        from unittest.mock import AsyncMock, patch

        original_content = """# Introduction

Python is a programming language.

# Core Concepts

Functions and classes are important.
"""

        llm_response = """Changes: Made introduction more engaging and expanded core concepts

Revised Content:
# Introduction

Python is a powerful, versatile programming language loved by developers worldwide.

# Core Concepts

Functions and classes are fundamental building blocks that enable code reusability and organization.
"""

        with patch("src.agents.revision.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            result = await revise_article(
                original_content,
                "Make the introduction more engaging",
                topic="Python Programming",
            )

            assert isinstance(result, RevisedArticle)
            assert "powerful, versatile" in result.content
            assert "Made introduction more engaging" in result.changes_summary
            assert result.word_count > 0
            assert result.revision_number == 1

            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_revise_article_with_revision_number(self):
        """Test revision number parameter."""
        from unittest.mock import AsyncMock, patch

        llm_response = """Changes: Fixed typos
Revised Content:
# Fixed content
"""

        with patch("src.agents.revision.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            result = await revise_article("# Content", "Fix typos", topic="Test", revision_number=2)

            assert result.revision_number == 2

    @pytest.mark.asyncio
    async def test_revise_article_validation_empty_content(self):
        """Should reject empty content."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            await revise_article("", "Feedback", topic="Test")

        with pytest.raises(ValueError, match="content cannot be empty"):
            await revise_article("   ", "Feedback", topic="Test")

    @pytest.mark.asyncio
    async def test_revise_article_validation_empty_feedback(self):
        """Should reject empty feedback."""
        with pytest.raises(ValueError, match="feedback cannot be empty"):
            await revise_article("# Content", "", topic="Test")

        with pytest.raises(ValueError, match="feedback cannot be empty"):
            await revise_article("# Content", "   ", topic="Test")

    @pytest.mark.asyncio
    async def test_revise_article_validation_empty_topic(self):
        """Should reject empty topic."""
        with pytest.raises(ValueError, match="topic cannot be empty"):
            await revise_article("# Content", "Feedback", topic="")

        with pytest.raises(ValueError, match="topic cannot be empty"):
            await revise_article("# Content", "Feedback", topic="   ")

    @pytest.mark.asyncio
    async def test_revise_article_validation_invalid_revision_number(self):
        """Should reject invalid revision number."""
        with pytest.raises(ValueError, match="revision_number must be"):
            await revise_article("# Content", "Feedback", topic="Test", revision_number=0)

        with pytest.raises(ValueError, match="revision_number must be"):
            await revise_article("# Content", "Feedback", topic="Test", revision_number=-1)

    @pytest.mark.asyncio
    async def test_revise_article_validation_invalid_temperature(self):
        """Should reject invalid temperature."""
        with pytest.raises(ValueError, match="temperature must be"):
            await revise_article("# Content", "Feedback", topic="Test", temperature=-0.1)

        with pytest.raises(ValueError, match="temperature must be"):
            await revise_article("# Content", "Feedback", topic="Test", temperature=2.5)

    @pytest.mark.asyncio
    async def test_revise_article_empty_llm_response(self):
        """Should raise error if LLM returns empty."""
        from unittest.mock import AsyncMock, patch

        with patch("src.agents.revision.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ""

            with pytest.raises(ValueError, match="LLM returned empty revision"):
                await revise_article("# Content", "Feedback", topic="Test")

    @pytest.mark.asyncio
    async def test_revise_article_word_count(self):
        """Word count should be calculated correctly."""
        from unittest.mock import AsyncMock, patch

        llm_response = """Changes: Test
Revised Content:
One two three four five six seven
"""

        with patch("src.agents.revision.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            result = await revise_article("# Content", "Feedback", topic="Test")

            assert result.word_count == 7

    @pytest.mark.asyncio
    async def test_revise_article_immutability(self):
        """Input content should never be mutated."""
        from unittest.mock import AsyncMock, patch

        original_content = "# Original\n\nThis is original."
        original_feedback = "Change it"

        llm_response = """Changes: Changed
Revised Content:
# Modified

This is modified.
"""

        with patch("src.agents.revision.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            await revise_article(original_content, original_feedback, topic="Test")

            # Originals should be unchanged
            assert original_content == "# Original\n\nThis is original."
            assert original_feedback == "Change it"

    @pytest.mark.asyncio
    async def test_revise_article_model_parameter(self):
        """Model parameter should be passed to LLM."""
        from unittest.mock import AsyncMock, patch

        llm_response = """Changes: Updated
Revised Content:
# Content
"""

        with patch("src.agents.revision.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            await revise_article("# Content", "Feedback", topic="Test", model="gpt-4")

            call_kwargs = mock_llm.call_args.kwargs
            assert call_kwargs.get("model") == "gpt-4"

    @pytest.mark.asyncio
    async def test_revise_article_temperature_parameter(self):
        """Temperature parameter should be passed to LLM."""
        from unittest.mock import AsyncMock, patch

        llm_response = """Changes: Updated
Revised Content:
# Content
"""

        with patch("src.agents.revision.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            await revise_article("# Content", "Feedback", topic="Test", temperature=0.6)

            call_kwargs = mock_llm.call_args.kwargs
            assert call_kwargs.get("temperature") == 0.6

    @pytest.mark.asyncio
    async def test_revise_article_preserves_formatting(self):
        """Should preserve markdown formatting."""
        from unittest.mock import AsyncMock, patch

        llm_response = """Changes: Minor edits
Revised Content:
# Title

**Bold text** and `code` formatting.

```python
def example():
    pass
```
"""

        with patch("src.agents.revision.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            result = await revise_article("# Old", "Improve", topic="Test")

            assert "**Bold text**" in result.content
            assert "`code`" in result.content
            assert "```python" in result.content

    @pytest.mark.asyncio
    async def test_revise_article_multiple_cycles(self):
        """Test multiple revision cycles."""
        from unittest.mock import AsyncMock, patch

        with patch("src.agents.revision.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Changes: Rev 1\nRevised Content:\n# First"

            result1 = await revise_article(
                "# Original", "Change 1", topic="Test", revision_number=1
            )
            assert result1.revision_number == 1

            mock_llm.return_value = "Changes: Rev 2\nRevised Content:\n# Second"
            result2 = await revise_article(
                result1.content, "Change 2", topic="Test", revision_number=2
            )
            assert result2.revision_number == 2

            mock_llm.return_value = "Changes: Rev 3\nRevised Content:\n# Third"
            result3 = await revise_article(
                result2.content, "Change 3", topic="Test", revision_number=3
            )
            assert result3.revision_number == 3
