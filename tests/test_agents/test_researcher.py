"""Tests for the researcher agent.

Tests cover:
- Multi-source research (web, papers, code)
- Intelligent source selection based on topic/section
- Citation generation
- LLM synthesis
- Input validation
- Error handling
"""

import pytest

from src.agents.researcher import (
    ResearchDossier,
    _build_citations,
    _extract_language_from_topic,
    _should_search_code,
    _should_search_papers,
    research_section,
)
from src.agents.structure_planner import Section, generate_outline


class TestHelperFunctions:
    """Tests for internal helper functions."""

    def test_should_search_papers_with_academic_keywords(self):
        """Papers should be searched for academic topics."""
        assert _should_search_papers("Machine Learning Theory", "Advanced Techniques")
        assert _should_search_papers("Neural Networks", "Architecture")
        assert _should_search_papers("Deep Reinforcement Learning", "Algorithms")

    def test_should_search_papers_without_academic_keywords(self):
        """Papers should not be searched for non-academic topics."""
        assert not _should_search_papers("Python Tutorial", "Getting Started")
        assert not _should_search_papers("Web Development", "Building Apps")

    def test_should_search_code_with_practical_keywords(self):
        """Code should be searched for practical topics."""
        assert _should_search_code("Python Async", "Practical Implementation")
        assert _should_search_code("Building REST APIs", "Tutorial")
        assert _should_search_code("Creating Web Apps", "Code Examples")

    def test_should_search_code_without_practical_keywords(self):
        """Code should not be searched for theoretical topics."""
        assert not _should_search_code("ML Theory", "Mathematical Foundations")
        assert not _should_search_code("Algorithm Analysis", "Complexity Theory")

    def test_extract_language_python(self):
        """Python language extraction."""
        assert _extract_language_from_topic("Python Async Programming") == "python"
        assert _extract_language_from_topic("Machine Learning with Python") == "python"

    def test_extract_language_javascript(self):
        """JavaScript language extraction."""
        assert _extract_language_from_topic("JavaScript Promises") == "javascript"
        assert _extract_language_from_topic("TypeScript Patterns") == "typescript"

    def test_extract_language_others(self):
        """Other language extraction."""
        assert _extract_language_from_topic("Rust Async") == "rust"
        assert _extract_language_from_topic("Go Concurrency") == "go"

    def test_extract_language_default(self):
        """Default to Python for ML/AI topics."""
        assert _extract_language_from_topic("Machine Learning") == "python"
        assert _extract_language_from_topic("Neural Networks") == "python"

    def test_build_citations_web_only(self):
        """Build citations from web results only."""
        web_results = [
            {"title": "Guide to Python", "url": "https://example.com/1"},
            {"title": "Advanced Techniques", "url": "https://example.com/2"},
        ]
        citations = _build_citations(web_results, [], [])

        assert len(citations) == 2
        assert "[1] Guide to Python - https://example.com/1" in citations
        assert "[2] Advanced Techniques - https://example.com/2" in citations

    def test_build_citations_all_sources(self):
        """Build citations from all source types."""
        web_results = [{"title": "Web Article", "url": "https://example.com/web"}]
        papers = [
            {
                "title": "Research Paper",
                "entry_id": "https://arxiv.org/abs/1234.5678",
                "authors": ["John Doe"],
            }
        ]
        code_examples = [{"name": "awesome/repo", "url": "https://github.com/awesome/repo"}]

        citations = _build_citations(web_results, papers, code_examples)

        assert len(citations) == 3
        assert any("Web Article" in c for c in citations)
        assert any("John Doe" in c and "Research Paper" in c for c in citations)
        assert any("GitHub: awesome/repo" in c for c in citations)

    def test_build_citations_limits_results(self):
        """Citations should be limited to top results."""
        web_results = [
            {"title": f"Article {i}", "url": f"https://example.com/{i}"} for i in range(10)
        ]

        citations = _build_citations(web_results, [], [])

        # Should only include top 5 web results
        assert len(citations) == 5


class TestResearchSection:
    """Tests for the main research_section function."""

    @pytest.mark.asyncio
    async def test_research_section_basic(self):
        """Test basic research functionality with mocked APIs."""
        from unittest.mock import AsyncMock, patch

        # Create test outline
        outline = generate_outline("Python Async Programming")
        section = outline.sections[1]  # Fundamentals section

        # Mock external API calls
        with (
            patch(
                "src.agents.researcher.search_tavily", new_callable=AsyncMock
            ) as mock_search_tavily,
            patch("src.agents.researcher.fetch_arxiv", new_callable=AsyncMock) as mock_fetch_arxiv,
            patch(
                "src.agents.researcher.fetch_github_trending", new_callable=AsyncMock
            ) as mock_fetch_github,
            patch(
                "src.agents.researcher.generate_text", new_callable=AsyncMock
            ) as mock_generate_text,
        ):
            mock_search_tavily.return_value = [
                {"title": "Async Guide", "url": "https://example.com", "content": "Content here"}
            ]
            mock_fetch_arxiv.return_value = []
            mock_fetch_github.return_value = []
            mock_generate_text.return_value = "Comprehensive synthesis of research findings."

            # Execute research
            result = await research_section(outline, section)

            # Verify result structure
            assert isinstance(result, ResearchDossier)
            assert result.section_title == section.title
            assert len(result.synthesis) > 0
            assert len(result.web_results) > 0
            assert len(result.citations) > 0

            # Verify API calls
            mock_search_tavily.assert_called_once()
            mock_generate_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_research_section_with_papers(self):
        """Test research with academic paper search enabled."""
        from unittest.mock import AsyncMock, patch

        # Create academic topic
        outline = generate_outline("Machine Learning Theory")
        section = outline.sections[1]

        # Mock APIs
        with (
            patch("src.agents.researcher.search_tavily", new_callable=AsyncMock) as mock_search,
            patch("src.agents.researcher.fetch_arxiv", new_callable=AsyncMock) as mock_fetch_arxiv,
            patch(
                "src.agents.researcher.fetch_github_trending", new_callable=AsyncMock
            ) as mock_fetch_github,
            patch("src.agents.researcher.generate_text", new_callable=AsyncMock) as mock_generate,
        ):
            mock_search.return_value = [{"title": "ML Guide", "url": "https://example.com"}]
            mock_fetch_arxiv.return_value = [
                {
                    "title": "Paper 1",
                    "entry_id": "arxiv:1234",
                    "summary": "Summary",
                    "authors": ["Author 1"],
                }
            ]
            mock_fetch_github.return_value = []
            mock_generate.return_value = "Research synthesis"

            # Execute
            result = await research_section(outline, section)

            # Should search papers for academic topics
            mock_fetch_arxiv.assert_called_once()
            assert len(result.papers) > 0

    @pytest.mark.asyncio
    async def test_research_section_with_code(self):
        """Test research with code example search enabled."""
        from unittest.mock import AsyncMock, patch

        # Create practical topic
        outline = generate_outline("Building REST APIs")
        section = outline.sections[2]  # Practical section

        # Mock APIs
        with (
            patch("src.agents.researcher.search_tavily", new_callable=AsyncMock) as mock_search,
            patch("src.agents.researcher.fetch_arxiv", new_callable=AsyncMock) as mock_fetch_arxiv,
            patch(
                "src.agents.researcher.fetch_github_trending", new_callable=AsyncMock
            ) as mock_fetch_github,
            patch("src.agents.researcher.generate_text", new_callable=AsyncMock) as mock_generate,
        ):
            mock_search.return_value = [{"title": "API Guide", "url": "https://example.com"}]
            mock_fetch_arxiv.return_value = []
            mock_fetch_github.return_value = [
                {
                    "name": "awesome/api",
                    "url": "https://github.com/awesome/api",
                    "description": "API lib",
                }
            ]
            mock_generate.return_value = "Research synthesis"

            # Execute
            result = await research_section(outline, section)

            # Should search code for practical topics
            mock_fetch_github.assert_called_once()
            assert len(result.code_examples) > 0

    @pytest.mark.asyncio
    async def test_research_section_validation_none_outline(self):
        """Should reject None outline."""
        section = Section(title="Test", subsections=("Sub1",))

        with pytest.raises(ValueError, match="outline cannot be None"):
            await research_section(None, section)

    @pytest.mark.asyncio
    async def test_research_section_validation_none_section(self):
        """Should reject None section."""
        outline = generate_outline("Python")

        with pytest.raises(ValueError, match="section cannot be None"):
            await research_section(outline, None)

    @pytest.mark.asyncio
    async def test_research_section_validation_section_not_in_outline(self):
        """Should reject section not in outline."""
        outline = generate_outline("Python")
        wrong_section = Section(title="Not In Outline", subsections=("Sub1",))

        with pytest.raises(ValueError, match="not in the provided outline"):
            await research_section(outline, wrong_section)

    @pytest.mark.asyncio
    async def test_research_section_validation_invalid_limits(self):
        """Should reject invalid limits."""
        outline = generate_outline("Python")
        section = outline.sections[0]

        with pytest.raises(ValueError, match="All limits must be at least 1"):
            await research_section(outline, section, web_search_limit=0)

        with pytest.raises(ValueError, match="All limits must be at least 1"):
            await research_section(outline, section, paper_limit=-1)

    @pytest.mark.asyncio
    async def test_research_section_handles_api_failures(self):
        """Research should continue even if some APIs fail."""
        from unittest.mock import AsyncMock, patch

        outline = generate_outline("Machine Learning")
        section = outline.sections[1]

        # Mock web search success, paper/code search failures, synthesis success
        with (
            patch("src.agents.researcher.search_tavily", new_callable=AsyncMock) as mock_search,
            patch("src.agents.researcher.fetch_arxiv", new_callable=AsyncMock) as mock_arxiv,
            patch(
                "src.agents.researcher.fetch_github_trending", new_callable=AsyncMock
            ) as mock_github,
            patch("src.agents.researcher.generate_text", new_callable=AsyncMock) as mock_generate,
        ):
            mock_search.return_value = [{"title": "Guide", "url": "https://example.com"}]
            mock_arxiv.side_effect = Exception("API Error")
            mock_github.side_effect = Exception("API Error")
            mock_generate.return_value = "Synthesis based on web results only"

            # Should still complete with web results
            result = await research_section(outline, section)

            assert isinstance(result, ResearchDossier)
            assert len(result.web_results) > 0
            assert len(result.papers) == 0  # Failed
            assert len(result.code_examples) == 0  # Failed
            assert result.synthesis  # Still got synthesis

    @pytest.mark.asyncio
    async def test_research_section_empty_synthesis_error(self):
        """Should raise error if LLM returns empty synthesis."""
        from unittest.mock import AsyncMock, patch

        outline = generate_outline("Python")
        section = outline.sections[0]

        with (
            patch("src.agents.researcher.search_tavily", new_callable=AsyncMock) as mock_search,
            patch("src.agents.researcher.fetch_arxiv", new_callable=AsyncMock) as mock_arxiv,
            patch(
                "src.agents.researcher.fetch_github_trending", new_callable=AsyncMock
            ) as mock_github,
            patch("src.agents.researcher.generate_text", new_callable=AsyncMock) as mock_generate,
        ):
            mock_search.return_value = [{"title": "Test", "url": "http://ex.com"}]
            mock_arxiv.return_value = []
            mock_github.return_value = []
            mock_generate.return_value = ""

            with pytest.raises(ValueError, match="LLM returned empty synthesis"):
                await research_section(outline, section)

    @pytest.mark.asyncio
    async def test_research_section_immutability(self):
        """Outline and Section should never be mutated."""
        from unittest.mock import AsyncMock, patch

        outline = generate_outline("Python")
        section = outline.sections[0]

        # Get original values
        original_topic = outline.topic
        original_sections = outline.sections
        original_title = section.title

        # Mock APIs
        with (
            patch("src.agents.researcher.search_tavily", new_callable=AsyncMock) as mock_search,
            patch("src.agents.researcher.fetch_arxiv", new_callable=AsyncMock) as mock_arxiv,
            patch(
                "src.agents.researcher.fetch_github_trending", new_callable=AsyncMock
            ) as mock_github,
            patch("src.agents.researcher.generate_text", new_callable=AsyncMock) as mock_generate,
        ):
            mock_search.return_value = [{"title": "Test", "url": "http://ex.com"}]
            mock_arxiv.return_value = []
            mock_github.return_value = []
            mock_generate.return_value = "Synthesis"

            # Execute research
            await research_section(outline, section)

            # Verify immutability
            assert outline.topic == original_topic
            assert outline.sections == original_sections
            assert section.title == original_title
