"""Tests for the reviewer agent.

Tests cover:
- Article review and polishing
- SEO metadata generation (title, subtitle, tags)
- Content parsing and extraction
- Input validation
- Error handling
"""

import pytest

from src.agents.reviewer import (
    ReviewedArticle,
    _count_words,
    _extract_field,
    _extract_tags_from_response,
    review_article,
)


class TestHelperFunctions:
    """Tests for internal helper functions."""

    def test_count_words_normal(self):
        """Count words in normal text."""
        assert _count_words("Hello world") == 2
        assert _count_words("One two three") == 3

    def test_count_words_empty(self):
        """Empty string returns 0."""
        assert _count_words("") == 0
        assert _count_words("   ") == 0

    def test_count_words_markdown(self):
        """Count words in markdown content."""
        markdown = "# Title\n\nThis is content."
        assert _count_words(markdown) == 5

    def test_extract_tags_from_tags_line(self):
        """Extract tags from 'Tags:' format."""
        response = "Tags: python, async, programming, tutorial"
        tags = _extract_tags_from_response(response)

        assert len(tags) >= 4
        assert "python" in tags
        assert "async" in tags
        assert "programming" in tags

    def test_extract_tags_from_hashtags(self):
        """Extract tags from hashtag format."""
        response = "Here are the tags: #python #async #programming"
        tags = _extract_tags_from_response(response)

        assert "python" in tags
        assert "async" in tags
        assert "programming" in tags

    def test_extract_tags_deduplication(self):
        """Tags should be deduplicated."""
        response = "Tags: python, python, async, async, tutorial"
        tags = _extract_tags_from_response(response)

        # Should not have duplicates
        assert len(tags) == len(set(tags))

    def test_extract_tags_limit(self):
        """Tags should be limited to 7."""
        response = "Tags: tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8, tag9"
        tags = _extract_tags_from_response(response)

        assert len(tags) <= 7

    def test_extract_field_basic(self):
        """Extract field from response."""
        response = "Title: My Great Article\nContent here"
        title = _extract_field(response, "Title")

        assert title == "My Great Article"

    def test_extract_field_with_quotes(self):
        """Field extraction should remove quotes."""
        response = 'Title: "My Article"\nContent'
        title = _extract_field(response, "Title")

        assert title == "My Article"

    def test_extract_field_case_insensitive(self):
        """Field extraction should be case insensitive."""
        response = "title: Article Title\nContent"
        title = _extract_field(response, "Title")

        assert title == "Article Title"

    def test_extract_field_not_found(self):
        """Missing field returns empty string."""
        response = "Content: Some content here"
        title = _extract_field(response, "Title")

        assert title == ""


class TestReviewArticle:
    """Tests for the main review_article function."""

    @pytest.mark.asyncio
    async def test_review_article_basic(self):
        """Test basic article review with mocked LLM."""
        from unittest.mock import AsyncMock, patch

        article_content = """# Introduction

Python async programming enables concurrent execution.
This guide covers the fundamentals and best practices.

# Core Concepts

Async and await keywords make asynchronous code readable.
Event loops manage the execution of coroutines.
"""

        llm_response = """Title: Mastering Python Async Programming
Subtitle: A comprehensive guide to concurrent programming in Python with practical examples
Tags: python, async, programming, concurrency, tutorial
Readability: College Level
Improvements: Fixed grammar, improved clarity, optimized for SEO

Polished Content:
# Introduction

Python async programming enables concurrent execution of tasks.
This comprehensive guide covers the fundamentals and best practices.

# Core Concepts

The async and await keywords make asynchronous code highly readable.
Event loops efficiently manage the execution of coroutines.
"""

        with patch("src.agents.reviewer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            result = await review_article("Python Async Programming", article_content)

            assert isinstance(result, ReviewedArticle)
            assert result.seo_title == "Mastering Python Async Programming"
            assert len(result.seo_subtitle) > 0
            assert len(result.tags) >= 5
            assert result.word_count > 0
            assert len(result.polished_content) > 0

            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_review_article_with_tags(self):
        """Test tag extraction and formatting."""
        from unittest.mock import AsyncMock, patch

        content = "# Article\n\nContent here."

        llm_response = """Title: Test Article
Subtitle: A test article about testing
Tags: testing, python, automation, quality, development, ci-cd
Readability: Professional
Improvements: General improvements

Polished Content:
# Article

Improved content here.
"""

        with patch("src.agents.reviewer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            result = await review_article("Testing", content)

            assert len(result.tags) >= 5
            assert "testing" in result.tags
            assert "python" in result.tags
            assert all(isinstance(tag, str) for tag in result.tags)

    @pytest.mark.asyncio
    async def test_review_article_validation_empty_topic(self):
        """Should reject empty topic."""
        with pytest.raises(ValueError, match="topic cannot be empty"):
            await review_article("", "Content here")

        with pytest.raises(ValueError, match="topic cannot be empty"):
            await review_article("   ", "Content here")

    @pytest.mark.asyncio
    async def test_review_article_validation_empty_content(self):
        """Should reject empty content."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            await review_article("Topic", "")

        with pytest.raises(ValueError, match="content cannot be empty"):
            await review_article("Topic", "   ")

    @pytest.mark.asyncio
    async def test_review_article_validation_invalid_tags(self):
        """Should reject invalid tag limits."""
        with pytest.raises(ValueError, match="Invalid tag limits"):
            await review_article("Topic", "Content", min_tags=0)

        with pytest.raises(ValueError, match="Invalid tag limits"):
            await review_article("Topic", "Content", min_tags=10, max_tags=5)

    @pytest.mark.asyncio
    async def test_review_article_validation_invalid_temperature(self):
        """Should reject invalid temperature."""
        with pytest.raises(ValueError, match="temperature must be"):
            await review_article("Topic", "Content", temperature=-0.1)

        with pytest.raises(ValueError, match="temperature must be"):
            await review_article("Topic", "Content", temperature=2.5)

    @pytest.mark.asyncio
    async def test_review_article_empty_llm_response(self):
        """Should raise error if LLM returns empty."""
        from unittest.mock import AsyncMock, patch

        with patch("src.agents.reviewer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ""

            with pytest.raises(ValueError, match="LLM returned empty review"):
                await review_article("Topic", "Content here")

    @pytest.mark.asyncio
    async def test_review_article_fallback_title(self):
        """Should generate fallback title if not provided."""
        from unittest.mock import AsyncMock, patch

        llm_response = """Subtitle: Some subtitle
Tags: tag1, tag2, tag3, tag4, tag5
Readability: College
Improvements: Made improvements

Polished Content:
Content here
"""

        with patch("src.agents.reviewer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            result = await review_article("Python", "# Content")

            # Should have fallback title
            assert result.seo_title
            assert "Python" in result.seo_title

    @pytest.mark.asyncio
    async def test_review_article_fallback_subtitle(self):
        """Should generate fallback subtitle if not provided."""
        from unittest.mock import AsyncMock, patch

        llm_response = """Title: Great Article
Tags: tag1, tag2, tag3, tag4, tag5
Readability: College
Improvements: Improvements

Polished Content:
Content
"""

        with patch("src.agents.reviewer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            result = await review_article("Python", "# Content")

            # Should have fallback subtitle
            assert result.seo_subtitle
            assert "Python" in result.seo_subtitle

    @pytest.mark.asyncio
    async def test_review_article_fallback_tags(self):
        """Should generate fallback tags if insufficient."""
        from unittest.mock import AsyncMock, patch

        llm_response = """Title: Article
Subtitle: Description
Tags: tag1, tag2
Readability: College
Improvements: Done

Polished Content:
Content
"""

        with patch("src.agents.reviewer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            result = await review_article("Machine Learning", "# Content", min_tags=5)

            # Should have at least min_tags
            assert len(result.tags) >= 5

    @pytest.mark.asyncio
    async def test_review_article_word_count(self):
        """Word count should be calculated correctly."""
        from unittest.mock import AsyncMock, patch

        llm_response = """Title: Test
Subtitle: Test subtitle
Tags: tag1, tag2, tag3, tag4, tag5
Readability: College
Improvements: None

Polished Content:
One two three four five
"""

        with patch("src.agents.reviewer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            result = await review_article("Topic", "# Content")

            assert result.word_count == 5

    @pytest.mark.asyncio
    async def test_review_article_immutability(self):
        """Input content should never be mutated."""
        from unittest.mock import AsyncMock, patch

        original_content = "# Original Content\n\nThis is the original."

        llm_response = """Title: Test
Subtitle: Test
Tags: a, b, c, d, e
Readability: College
Improvements: None

Polished Content:
# Modified Content

This is modified.
"""

        with patch("src.agents.reviewer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            await review_article("Topic", original_content)

            # Original should be unchanged
            assert original_content == "# Original Content\n\nThis is the original."

    @pytest.mark.asyncio
    async def test_review_article_model_parameter(self):
        """Model parameter should be passed to LLM."""
        from unittest.mock import AsyncMock, patch

        llm_response = """Title: T
Subtitle: S
Tags: a, b, c, d, e
Readability: C
Improvements: I

Polished Content:
Content
"""

        with patch("src.agents.reviewer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            await review_article("Topic", "Content", model="gpt-4")

            call_kwargs = mock_llm.call_args.kwargs
            assert call_kwargs.get("model") == "gpt-4"

    @pytest.mark.asyncio
    async def test_review_article_temperature_parameter(self):
        """Temperature parameter should be passed to LLM."""
        from unittest.mock import AsyncMock, patch

        llm_response = """Title: T
Subtitle: S
Tags: a, b, c, d, e
Readability: C
Improvements: I

Polished Content:
Content
"""

        with patch("src.agents.reviewer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response

            await review_article("Topic", "Content", temperature=0.5)

            call_kwargs = mock_llm.call_args.kwargs
            assert call_kwargs.get("temperature") == 0.5
