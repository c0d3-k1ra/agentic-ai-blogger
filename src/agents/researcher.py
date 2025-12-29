"""Researcher Agent - Deep research for article sections.

Conducts comprehensive research for article sections using multiple sources:
- Web search via Tavily
- Academic papers via arXiv
- Code examples via GitHub Trending
- LLM-powered synthesis and summarization

Public API:
    research_section: Conduct deep research for exactly one article section
    ResearchDossier: Immutable dataclass containing research findings and citations

Design Principles:
- Research exactly one section at a time
- Multi-source data collection (web, papers, code)
- Structured input/output contracts
- Pure function with minimal side effects (API calls + LLM)
- Fully testable with mocked external services

Example:
    >>> outline = generate_outline("Python Async Programming")
    >>> section = outline.sections[1]  # Fundamentals section
    >>> dossier = await research_section(outline, section)
    >>> print(dossier.section_title)
    'Understanding the Fundamentals'
    >>> len(dossier.web_results) > 0
    True
    >>> len(dossier.citations) > 0
    True
"""

from dataclasses import dataclass

from src.agents.structure_planner import Outline, Section
from src.integrations.llm_client import generate_text
from src.integrations.prompts import RESEARCH_SYNTHESIS_PROMPT_V1
from src.integrations.search.arxiv_client import fetch_arxiv
from src.integrations.search.github_trending_client import fetch_github_trending
from src.integrations.search.tavily_client import search_tavily


@dataclass(frozen=True)
class ResearchDossier:
    """Research findings for a single article section.

    Represents comprehensive research data from multiple sources,
    synthesized and ready for use by the writer agent.

    Attributes:
        section_title: The section title being researched
        synthesis: LLM-generated summary of all research findings
        web_results: List of web search results (from Tavily)
        papers: List of arXiv papers (if applicable)
        code_examples: List of GitHub repositories (if applicable)
        citations: List of formatted citations for reference
    """

    section_title: str
    synthesis: str
    web_results: tuple[dict, ...]
    papers: tuple[dict, ...]
    code_examples: tuple[dict, ...]
    citations: tuple[str, ...]


def _should_search_papers(topic: str, section_title: str) -> bool:
    """Determine if arXiv paper search is relevant.

    Papers are most relevant for topics with academic/research nature.

    Args:
        topic: The article topic
        section_title: The section being researched

    Returns:
        True if arXiv search should be performed

    Examples:
        >>> _should_search_papers("Machine Learning Theory", "Advanced Techniques")
        True
        >>> _should_search_papers("Python Async", "Getting Started Tutorial")
        False
    """
    # Keywords indicating academic/research content
    academic_keywords = [
        "learning",
        "neural",
        "algorithm",
        "research",
        "theory",
        "model",
        "advanced",
        "deep",
        "reinforcement",
        "transformer",
        "attention",
        "optimization",
    ]

    combined = f"{topic} {section_title}".lower()

    # Check if any academic keyword is present
    return any(keyword in combined for keyword in academic_keywords)


def _should_search_code(topic: str, section_title: str) -> bool:
    """Determine if GitHub code search is relevant.

    Code examples are most relevant for practical/implementation sections.

    Args:
        topic: The article topic
        section_title: The section being researched

    Returns:
        True if GitHub search should be performed

    Examples:
        >>> _should_search_code("Python Async", "Practical Implementation")
        True
        >>> _should_search_code("ML Theory", "Mathematical Foundations")
        False
    """
    # Keywords indicating need for code examples
    code_keywords = [
        "implementation",
        "practical",
        "code",
        "example",
        "tutorial",
        "guide",
        "how to",
        "building",
        "creating",
        "project",
        "application",
        "framework",
    ]

    combined = f"{topic} {section_title}".lower()

    # Check if any code-related keyword is present
    return any(keyword in combined for keyword in code_keywords)


def _extract_language_from_topic(topic: str) -> str:
    """Extract programming language from topic for GitHub search.

    Args:
        topic: The article topic

    Returns:
        Programming language name (defaults to 'python')

    Examples:
        >>> _extract_language_from_topic("JavaScript Promises")
        'javascript'
        >>> _extract_language_from_topic("Rust Async Programming")
        'rust'
        >>> _extract_language_from_topic("Machine Learning")
        'python'
    """
    topic_lower = topic.lower()

    # Common programming languages
    languages = ["python", "javascript", "typescript", "rust", "go", "java", "cpp", "csharp"]

    for lang in languages:
        if lang in topic_lower or lang.replace("script", "") in topic_lower:
            return lang

    # Default to Python for ML/AI topics
    return "python"


def _build_citations(
    web_results: list[dict], papers: list[dict], code_examples: list[dict]
) -> list[str]:
    """Build formatted citations from research sources.

    Args:
        web_results: Web search results
        papers: arXiv papers
        code_examples: GitHub repositories

    Returns:
        List of formatted citation strings

    Examples:
        >>> web = [{"title": "Guide to Python", "url": "https://example.com"}]
        >>> _build_citations(web, [], [])
        ['[1] Guide to Python - https://example.com']
    """
    citations = []
    counter = 1

    # Add web results (top 5)
    for result in web_results[:5]:
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        if url:
            citations.append(f"[{counter}] {title} - {url}")
            counter += 1

    # Add papers (top 3)
    for paper in papers[:3]:
        title = paper.get("title", "Untitled")
        url = paper.get("entry_id", "")
        authors = paper.get("authors", [])
        author_str = authors[0] if authors else "Unknown"

        if url:
            citations.append(f"[{counter}] {author_str} et al. - {title} - {url}")
            counter += 1

    # Add code examples (top 3)
    for repo in code_examples[:3]:
        name = repo.get("name", "Untitled")
        url = repo.get("url", "")
        if url:
            citations.append(f"[{counter}] GitHub: {name} - {url}")
            counter += 1

    return citations


def _format_web_results(results: list[dict]) -> str:
    """Format web search results for prompt.

    Args:
        results: Web search results from Tavily

    Returns:
        Formatted string with top 5 results
    """
    if not results:
        return "No web results available."

    formatted = "\n\n".join(
        f"Title: {r.get('title', 'N/A')}\n"
        + f"Content: {r.get('content', r.get('summary', 'N/A'))[:500]}"
        for r in results[:5]
    )
    return formatted if formatted else "No web results available."


def _format_papers(papers: list[dict]) -> str:
    """Format arXiv papers for prompt.

    Args:
        papers: arXiv papers from fetch_arxiv

    Returns:
        Formatted string with top 3 papers
    """
    if not papers:
        return "No papers available."

    formatted = "\n\n".join(
        f"Title: {p.get('title', 'N/A')}\nSummary: {p.get('summary', 'N/A')[:500]}"
        for p in papers[:3]
    )
    return formatted if formatted else "No papers available."


def _format_code_examples(examples: list[dict]) -> str:
    """Format GitHub code examples for prompt.

    Args:
        examples: GitHub repositories from fetch_github_trending

    Returns:
        Formatted string with top 3 code examples
    """
    if not examples:
        return "No code examples available."

    formatted = "\n\n".join(
        f"Repository: {c.get('name', 'N/A')}\nDescription: {c.get('description', 'N/A')}"
        for c in examples[:3]
    )
    return formatted if formatted else "No code examples available."


def _build_synthesis_prompt(
    topic: str,
    section_title: str,
    web_results: list[dict],
    papers: list[dict],
    code_examples: list[dict],
) -> str:
    """Build prompt for LLM to synthesize research findings.

    Uses centralized prompt template from prompts.py with formatted research data.

    Args:
        topic: Article topic
        section_title: Section being researched
        web_results: Web search results
        papers: arXiv papers
        code_examples: GitHub repositories

    Returns:
        Formatted prompt string ready for LLM
    """
    # Format all research sources
    web_text = _format_web_results(web_results)
    papers_text = _format_papers(papers)
    code_text = _format_code_examples(code_examples)

    # Use centralized prompt template
    return RESEARCH_SYNTHESIS_PROMPT_V1.format(
        topic=topic,
        section_title=section_title,
        web_text=web_text,
        papers_text=papers_text,
        code_text=code_text,
    )


async def research_section(
    outline: Outline,
    section: Section,
    *,
    web_search_limit: int = 10,
    paper_limit: int = 5,
    code_limit: int = 5,
    model: str | None = None,
) -> ResearchDossier:
    """Conduct deep research for exactly one article section.

    Performs multi-source research including:
    1. Web search via Tavily (always)
    2. arXiv papers (if relevant to topic/section)
    3. GitHub repositories (if relevant to topic/section)
    4. LLM synthesis of all findings

    Args:
        outline: Complete article outline (provides context)
        section: Specific section to research (must be in outline.sections)
        web_search_limit: Max web results to fetch (default: 10)
        paper_limit: Max papers to fetch (default: 5)
        code_limit: Max code examples to fetch (default: 5)
        model: Optional LLM model override for synthesis

    Returns:
        ResearchDossier with findings, synthesis, and citations

    Raises:
        ValueError: If inputs invalid, section not in outline, or limits invalid
        httpx.HTTPError: If any API call fails
        LLMRetryExhausted: If synthesis generation fails

    Examples:
        >>> outline = generate_outline("Python Async Programming")
        >>> section = outline.sections[1]
        >>> dossier = await research_section(outline, section)
        >>> isinstance(dossier, ResearchDossier)
        True
        >>> dossier.section_title == section.title
        True
        >>> len(dossier.citations) > 0
        True

    Notes:
        - Input Outline and Section are never mutated (frozen dataclasses)
        - API calls and LLM synthesis are the only side effects
        - Results are deterministic given same inputs and same API responses
        - Fully testable by mocking external services
    """
    # 1. Validate inputs
    if outline is None:
        raise ValueError("outline cannot be None")

    if section is None:
        raise ValueError("section cannot be None")

    if section not in outline.sections:
        available_titles = [s.title for s in outline.sections]
        raise ValueError(
            f"Section '{section.title}' is not in the provided outline. "
            f"Available sections: {available_titles}"
        )

    if web_search_limit < 1 or paper_limit < 1 or code_limit < 1:
        raise ValueError("All limits must be at least 1")

    # 2. Build search query from topic and section
    search_query = f"{outline.topic} {section.title}"

    # 3. Perform web search (always)
    web_results = await search_tavily(search_query, limit=web_search_limit)

    # 4. Conditionally search arXiv papers
    papers = []
    if _should_search_papers(outline.topic, section.title):
        try:
            papers = await fetch_arxiv(search_query, max_results=paper_limit)
        except Exception:
            # Continue without papers if search fails
            papers = []

    # 5. Conditionally search GitHub code examples
    code_examples = []
    if _should_search_code(outline.topic, section.title):
        try:
            language = _extract_language_from_topic(outline.topic)
            code_examples = await fetch_github_trending(language=language)
            # Limit to requested amount
            code_examples = code_examples[:code_limit]
        except Exception:
            # Continue without code if search fails
            code_examples = []

    # 6. Build citations
    citations = _build_citations(web_results, papers, code_examples)

    # 7. Synthesize research using LLM
    synthesis_prompt = _build_synthesis_prompt(
        outline.topic, section.title, web_results, papers, code_examples
    )
    synthesis = await generate_text(synthesis_prompt, model=model, temperature=0.3)

    # 8. Validate synthesis is not empty
    if not synthesis or not synthesis.strip():
        raise ValueError("LLM returned empty synthesis")

    # 9. Return structured research dossier
    return ResearchDossier(
        section_title=section.title,
        synthesis=synthesis.strip(),
        web_results=tuple(web_results),
        papers=tuple(papers),
        code_examples=tuple(code_examples),
        citations=tuple(citations),
    )
