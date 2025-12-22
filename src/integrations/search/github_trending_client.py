"""GitHub Trending scraper.

Scrapes GitHub Trending page for popular repositories.
"""

import httpx
from bs4 import BeautifulSoup


async def fetch_github_trending(language: str = "python") -> list[dict]:
    """Scrape GitHub Trending page.

    Args:
        language: Programming language filter (e.g., 'python', 'javascript')

    Returns:
        List of raw scraped repository dictionaries

    Raises:
        httpx.HTTPError: If request fails
    """
    if not language or not language.strip():
        raise ValueError("Language cannot be empty")

    url = f"https://github.com/trending/{language.lower()}?since=daily"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30.0,
        )
        response.raise_for_status()

    # Parse HTML
    soup = BeautifulSoup(response.text, "html.parser")
    repos = []

    # Find all repository articles
    for article in soup.find_all("article", class_="Box-row"):
        try:
            # Extract repository name
            h2 = article.find("h2")
            if not h2:
                continue

            repo_link = h2.find("a")
            if not repo_link:
                continue

            repo_name = repo_link.get("href", "").strip("/")

            # Extract description
            desc_elem = article.find("p", class_="col-9")
            description = desc_elem.text.strip() if desc_elem else ""

            # Extract stars
            stars_elem = article.find("span", class_="d-inline-block float-sm-right")
            stars = stars_elem.text.strip() if stars_elem else "0"

            # Extract language
            lang_elem = article.find("span", {"itemprop": "programmingLanguage"})
            repo_language = lang_elem.text.strip() if lang_elem else language

            repo_dict = {
                "name": repo_name,
                "description": description,
                "stars": stars,
                "language": repo_language,
                "url": f"https://github.com/{repo_name}",
            }
            repos.append(repo_dict)

        except Exception:
            # Skip malformed entries
            continue

    return repos
