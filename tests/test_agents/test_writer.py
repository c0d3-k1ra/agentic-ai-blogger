"""Tests for Writer Agent.

This test suite verifies:
- WrittenSection dataclass immutability
- Word counting accuracy
- Prompt construction
- Input validation
- Main write_section function with mocked LLM
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.structure_planner import generate_outline
from src.agents.writer import (
    WrittenSection,
    _build_section_prompt,
    _count_words,
    _validate_inputs,
    write_section,
)


class TestWrittenSection:
    """Test WrittenSection dataclass."""

    def test_frozen_dataclass(self):
        """Test that WrittenSection is frozen (immutable)."""
        written = WrittenSection(section_title="Introduction", content="Some content", word_count=2)

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            written.section_title = "New Title"

        with pytest.raises(Exception):
            written.content = "New Content"

        with pytest.raises(Exception):
            written.word_count = 10

    def test_field_types(self):
        """Test that fields have correct types."""
        written = WrittenSection(section_title="Test", content="Content here", word_count=2)

        assert isinstance(written.section_title, str)
        assert isinstance(written.content, str)
        assert isinstance(written.word_count, int)

    def test_hashable(self):
        """Test that WrittenSection is hashable (can be in sets)."""
        written = WrittenSection(section_title="Test", content="Content", word_count=1)

        # Should not raise
        hash(written)

        # Can be added to set
        written_set = {written}
        assert written in written_set


class TestCountWords:
    """Test word counting function."""

    def test_normal_text(self):
        """Test counting words in normal text."""
        assert _count_words("Hello world") == 2
        assert _count_words("One two three four") == 4
        assert _count_words("Single") == 1

    def test_empty_string(self):
        """Test that empty string returns 0."""
        assert _count_words("") == 0

    def test_whitespace_only(self):
        """Test that whitespace-only string returns 0."""
        assert _count_words("   ") == 0
        assert _count_words("\n\n\n") == 0
        assert _count_words("\t\t") == 0

    def test_markdown_content(self):
        """Test counting words in markdown content."""
        markdown = "# Title\n\nThis is a paragraph."
        # Should count: #, Title, This, is, a, paragraph. = 6 words
        assert _count_words(markdown) == 6

    def test_code_blocks(self):
        """Test counting words with code blocks."""
        content = "Here is code:\n```python\nprint('hello')\n```\nDone."
        # Counts all tokens including code
        word_count = _count_words(content)
        assert word_count > 0

    def test_multiple_spaces(self):
        """Test that multiple spaces are handled correctly."""
        assert _count_words("word1    word2") == 2
        assert _count_words("a  b  c") == 3

    def test_newlines(self):
        """Test that newlines are treated as whitespace."""
        assert _count_words("word1\nword2\nword3") == 3


class TestBuildSectionPrompt:
    """Test prompt construction."""

    def test_contains_topic(self):
        """Test that prompt contains the topic."""
        outline = generate_outline("Python Async Programming", max_sections=3)
        section = outline.sections[0]

        prompt = _build_section_prompt(outline, section, 300)

        assert "Python Async Programming" in prompt

    def test_contains_section_title(self):
        """Test that prompt contains section title."""
        outline = generate_outline("Machine Learning", max_sections=3)
        section = outline.sections[0]

        prompt = _build_section_prompt(outline, section, 400)

        assert section.title in prompt

    def test_contains_subsections(self):
        """Test that prompt contains subsections."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        prompt = _build_section_prompt(outline, section, 500)

        # Check that all subsections are in the prompt
        for subsection in section.subsections:
            assert subsection in prompt

    def test_contains_target_words(self):
        """Test that prompt contains target word count."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        prompt = _build_section_prompt(outline, section, 250)

        assert "250" in prompt

    def test_deterministic_output(self):
        """Test that same inputs produce same prompt."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        prompt1 = _build_section_prompt(outline, section, 300)
        prompt2 = _build_section_prompt(outline, section, 300)

        assert prompt1 == prompt2

    def test_subsections_formatted_as_list(self):
        """Test that subsections are formatted as bulleted list."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        prompt = _build_section_prompt(outline, section, 300)

        # Should have "- " for list formatting
        for subsection in section.subsections:
            assert f"- {subsection}" in prompt

    def test_different_sections_different_prompts(self):
        """Test that different sections produce different prompts."""
        outline = generate_outline("Python", max_sections=4)

        prompt1 = _build_section_prompt(outline, outline.sections[0], 300)
        prompt2 = _build_section_prompt(outline, outline.sections[1], 300)

        # Prompts should be different (different section titles/subsections)
        assert prompt1 != prompt2


class TestValidateInputs:
    """Test input validation."""

    def test_none_outline_raises(self):
        """Test that None outline raises ValueError."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        with pytest.raises(ValueError, match="outline cannot be None"):
            _validate_inputs(None, section)

    def test_none_section_raises(self):
        """Test that None section raises ValueError."""
        outline = generate_outline("Python", max_sections=3)

        with pytest.raises(ValueError, match="section cannot be None"):
            _validate_inputs(outline, None)

    def test_section_not_in_outline_raises(self):
        """Test that section not in outline raises ValueError."""
        outline1 = generate_outline("Python", max_sections=3)
        outline2 = generate_outline("Java", max_sections=3)

        # Section from outline2, but validating against outline1
        section_from_other = outline2.sections[0]

        with pytest.raises(ValueError, match="not in the provided outline"):
            _validate_inputs(outline1, section_from_other)

    def test_valid_inputs_no_error(self):
        """Test that valid inputs don't raise errors."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        # Should not raise
        _validate_inputs(outline, section)

    def test_error_message_includes_available_sections(self):
        """Test that error message lists available sections."""
        outline1 = generate_outline("Python", max_sections=3)
        outline2 = generate_outline("Java", max_sections=3)

        section_from_other = outline2.sections[0]

        with pytest.raises(ValueError) as exc_info:
            _validate_inputs(outline1, section_from_other)

        error_msg = str(exc_info.value)
        # Should mention available sections
        assert "Available sections" in error_msg


class TestWriteSection:
    """Test main write_section function with mocked LLM."""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        """Test successful section writing with mocked LLM."""
        # Arrange
        outline = generate_outline("Python Async", max_sections=3)
        section = outline.sections[0]

        mock_content = """
Python async programming enables concurrent execution using coroutines.
This allows efficient handling of I/O-bound operations without blocking.
Async/await syntax makes asynchronous code more readable.
        """

        # Mock generate_text
        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_content

            # Act
            result = await write_section(outline, section, target_words=300)

            # Assert
            assert isinstance(result, WrittenSection)
            assert result.section_title == section.title
            assert result.content == mock_content.strip()
            assert result.word_count > 0

            # Verify LLM was called
            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_written_section(self):
        """Test that function returns WrittenSection instance."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Test content here"

            result = await write_section(outline, section)

            assert isinstance(result, WrittenSection)
            assert hasattr(result, "section_title")
            assert hasattr(result, "content")
            assert hasattr(result, "word_count")

    @pytest.mark.asyncio
    async def test_section_title_matches(self):
        """Test that section_title in result matches input section."""
        outline = generate_outline("Machine Learning", max_sections=3)
        section = outline.sections[1]  # Pick middle section

        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Content for this section"

            result = await write_section(outline, section)

            assert result.section_title == section.title

    @pytest.mark.asyncio
    async def test_word_count_computed(self):
        """Test that word_count is correctly computed from content."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        # Mock content with known word count
        mock_content = "One two three four five"  # 5 words

        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_content

            result = await write_section(outline, section)

            assert result.word_count == 5

    @pytest.mark.asyncio
    async def test_empty_llm_output_raises(self):
        """Test that empty LLM output raises ValueError."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ""

            with pytest.raises(ValueError, match="empty content"):
                await write_section(outline, section)

    @pytest.mark.asyncio
    async def test_whitespace_only_output_raises(self):
        """Test that whitespace-only LLM output raises ValueError."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "   \n\n   "

            with pytest.raises(ValueError, match="empty content"):
                await write_section(outline, section)

    @pytest.mark.asyncio
    async def test_target_words_validation(self):
        """Test that target_words < 50 raises ValueError."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        with pytest.raises(ValueError, match="at least 50"):
            await write_section(outline, section, target_words=10)

        with pytest.raises(ValueError, match="at least 50"):
            await write_section(outline, section, target_words=0)

    @pytest.mark.asyncio
    async def test_temperature_validation(self):
        """Test that temperature out of range raises ValueError."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        with pytest.raises(ValueError, match="between 0.0 and 2.0"):
            await write_section(outline, section, temperature=-0.1)

        with pytest.raises(ValueError, match="between 0.0 and 2.0"):
            await write_section(outline, section, temperature=2.5)

    @pytest.mark.asyncio
    async def test_input_immutability(self):
        """Test that inputs are not mutated."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        # Store original values
        original_topic = outline.topic
        original_sections_count = len(outline.sections)
        original_section_title = section.title

        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Test content"

            await write_section(outline, section)

            # Verify nothing changed
            assert outline.topic == original_topic
            assert len(outline.sections) == original_sections_count
            assert section.title == original_section_title

    @pytest.mark.asyncio
    async def test_different_sections(self):
        """Test writing different sections produces different results."""
        outline = generate_outline("Python", max_sections=4)

        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Test content"

            result1 = await write_section(outline, outline.sections[0])
            result2 = await write_section(outline, outline.sections[1])

            # Section titles should be different
            assert result1.section_title != result2.section_title

    @pytest.mark.asyncio
    async def test_model_parameter_passed(self):
        """Test that model parameter is passed to generate_text."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Test content"

            await write_section(outline, section, model="gpt-4")

            # Verify model was passed
            call_kwargs = mock_llm.call_args.kwargs
            assert call_kwargs.get("model") == "gpt-4"

    @pytest.mark.asyncio
    async def test_temperature_parameter_passed(self):
        """Test that temperature parameter is passed to generate_text."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Test content"

            await write_section(outline, section, temperature=0.9)

            # Verify temperature was passed
            call_kwargs = mock_llm.call_args.kwargs
            assert call_kwargs.get("temperature") == 0.9

    @pytest.mark.asyncio
    async def test_llm_called_once(self):
        """Test that LLM is called exactly once."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Test content"

            await write_section(outline, section)

            # Should be called exactly once
            assert mock_llm.call_count == 1

    @pytest.mark.asyncio
    async def test_prompt_contains_context(self):
        """Test that prompt passed to LLM contains all context."""
        outline = generate_outline("Python Async", max_sections=3)
        section = outline.sections[0]

        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Test content"

            await write_section(outline, section, target_words=300)

            # Get the prompt that was passed
            call_args = mock_llm.call_args
            prompt = call_args[0][0]

            # Verify context is in prompt
            assert outline.topic in prompt
            assert section.title in prompt
            assert "300" in prompt  # target_words

            # Verify subsections are in prompt
            for subsection in section.subsections:
                assert subsection in prompt

    @pytest.mark.asyncio
    async def test_content_is_stripped(self):
        """Test that leading/trailing whitespace is removed from content."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        mock_content = "\n\n  Test content here  \n\n"

        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_content

            result = await write_section(outline, section)

            # Content should be stripped
            assert result.content == "Test content here"
            assert not result.content.startswith(" ")
            assert not result.content.endswith(" ")

    @pytest.mark.asyncio
    async def test_section_not_in_outline_raises(self):
        """Test that section not in outline raises ValueError."""
        outline1 = generate_outline("Python", max_sections=3)
        outline2 = generate_outline("Java", max_sections=3)

        # Try to write section from outline2 with outline1 context
        section_from_other = outline2.sections[0]

        with pytest.raises(ValueError, match="not in the provided outline"):
            await write_section(outline1, section_from_other)

    @pytest.mark.asyncio
    async def test_default_parameters(self):
        """Test that default parameters work correctly."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Test content"

            # Call without optional parameters
            result = await write_section(outline, section)

            # Should succeed with defaults
            assert result is not None

            # Verify defaults were used
            call_kwargs = mock_llm.call_args.kwargs
            assert call_kwargs.get("temperature") == 0.7  # Default
            assert call_kwargs.get("model") is None  # Default

    @pytest.mark.asyncio
    async def test_markdown_content_preserved(self):
        """Test that markdown formatting in content is preserved."""
        outline = generate_outline("Python", max_sections=3)
        section = outline.sections[0]

        mock_content = """
# Subheading

This is **bold** and *italic* text.

```python
def hello():
    print("world")
```

- List item 1
- List item 2
        """

        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_content

            result = await write_section(outline, section)

            # Markdown should be preserved
            assert "**bold**" in result.content
            assert "*italic*" in result.content
            assert "```python" in result.content
            assert "- List item" in result.content


class TestIntegration:
    """Integration-style tests."""

    @pytest.mark.asyncio
    async def test_write_multiple_sections_sequentially(self):
        """Test writing multiple sections from same outline."""
        outline = generate_outline("Python", max_sections=4)

        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Test content for section"

            # Write each section
            results = []
            for section in outline.sections:
                result = await write_section(outline, section, target_words=200)
                results.append(result)

            # Should have written all sections
            assert len(results) == len(outline.sections)

            # Each should have matching title
            for result, section in zip(results, outline.sections):
                assert result.section_title == section.title

            # LLM should have been called once per section
            assert mock_llm.call_count == len(outline.sections)

    @pytest.mark.asyncio
    async def test_realistic_workflow(self):
        """Test realistic workflow: outline -> write intro -> verify."""
        # Generate outline
        outline = generate_outline("Advanced Python Design Patterns", max_sections=5)

        # Pick introduction section
        intro_section = outline.sections[0]

        # Mock realistic content
        realistic_content = """
Design patterns are reusable solutions to common software design problems. In Python,
these patterns leverage the language's dynamic features and flexibility. This article
explores advanced design patterns specifically tailored for Python development.

We'll examine creational, structural, and behavioral patterns, demonstrating how Python's
unique features like decorators, metaclasses, and first-class functions enable elegant
implementations that often surpass traditional approaches.
        """

        with patch("src.agents.writer.generate_text", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = realistic_content

            # Write introduction
            written = await write_section(outline, intro_section, target_words=100, temperature=0.7)

            # Verify structure
            assert written.section_title == intro_section.title
            assert "Design patterns" in written.content
            assert written.word_count > 50
            assert isinstance(written, WrittenSection)
