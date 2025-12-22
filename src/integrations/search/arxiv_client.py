"""arXiv papers client.

Fetches recent papers from arXiv.org.
"""

import arxiv


async def fetch_arxiv(query: str, max_results: int = 20) -> list[dict]:
    """Fetch recent arXiv papers matching query.

    Args:
        query: Search query string
        max_results: Maximum number of papers to return

    Returns:
        List of raw paper dictionaries with parsed arXiv data

    Raises:
        ValueError: If query is empty
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    if max_results <= 0:
        raise ValueError("Max results must be positive")

    # Create search client
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
    )

    # Fetch and parse results
    papers = []
    for result in search.results():
        paper_dict = {
            "entry_id": result.entry_id,
            "title": result.title,
            "summary": result.summary,
            "authors": [author.name for author in result.authors],
            "published": result.published.isoformat() if result.published else None,
            "updated": result.updated.isoformat() if result.updated else None,
            "primary_category": result.primary_category,
            "categories": result.categories,
            "pdf_url": result.pdf_url,
            "links": [link.href for link in result.links],
        }
        papers.append(paper_dict)

    return papers
