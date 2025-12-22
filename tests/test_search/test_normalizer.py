"""Tests for search result normalization."""

from datetime import datetime

import pytest

from src.integrations.search.normalizer import (
    normalize_arxiv,
    normalize_github_trending,
    normalize_google_trends,
    normalize_hackernews,
    normalize_tavily,
)


class TestNormalizeTavily:
    """Tests for Tavily result normalization."""

    def test_valid_input(self):
        """Test normalization of valid Tavily results."""
        raw_results = [
            {
                "title": "AI Trends 2024",
                "url": "https://example.com/ai-trends",
                "content": "Detailed analysis of AI trends in 2024",
                "published_date": "2024-01-15T10:00:00Z",
            }
        ]

        normalized = normalize_tavily(raw_results)

        assert len(normalized) == 1
        assert normalized[0]["title"] == "AI Trends 2024"
        assert normalized[0]["url"] == "https://example.com/ai-trends"
        assert normalized[0]["summary"] == "Detailed analysis of AI trends in 2024"
        assert normalized[0]["source"] == "tavily"
        assert isinstance(normalized[0]["published_at"], datetime)
        assert normalized[0]["raw"] == raw_results[0]

    def test_missing_title_skipped(self):
        """Test that results without title are skipped."""
        raw_results = [
            {"url": "https://example.com", "content": "Some content"},
            {"title": "", "url": "https://example.com", "content": "Content"},
        ]

        normalized = normalize_tavily(raw_results)

        assert len(normalized) == 0

    def test_missing_url_skipped(self):
        """Test that results without URL are skipped."""
        raw_results = [
            {"title": "Article", "content": "Some content"},
            {"title": "Article", "url": "", "content": "Content"},
        ]

        normalized = normalize_tavily(raw_results)

        assert len(normalized) == 0

    def test_summary_truncation(self):
        """Test that long summaries are truncated to 500 chars."""
        long_content = "a" * 600
        raw_results = [{"title": "Article", "url": "https://example.com", "content": long_content}]

        normalized = normalize_tavily(raw_results)

        assert len(normalized[0]["summary"]) == 500

    def test_published_at_none_when_missing(self):
        """Test that published_at is None when not provided."""
        raw_results = [{"title": "Article", "url": "https://example.com", "content": "Content"}]

        normalized = normalize_tavily(raw_results)

        assert normalized[0]["published_at"] is None

    def test_empty_input(self):
        """Test handling of empty input list."""
        normalized = normalize_tavily([])

        assert normalized == []

    def test_invalid_input_type(self):
        """Test that non-list input raises ValueError."""
        with pytest.raises(ValueError, match="must be a list"):
            normalize_tavily("not a list")


class TestNormalizeHackernews:
    """Tests for Hacker News result normalization."""

    def test_valid_input_with_url(self):
        """Test normalization of HN story with external URL."""
        raw_results = [
            {
                "id": 12345,
                "title": "Show HN: My Project",
                "url": "https://example.com",
                "time": 1704067200,  # 2024-01-01 00:00:00 UTC
            }
        ]

        normalized = normalize_hackernews(raw_results)

        assert len(normalized) == 1
        assert normalized[0]["title"] == "Show HN: My Project"
        assert normalized[0]["url"] == "https://example.com"
        assert normalized[0]["summary"] == ""
        assert normalized[0]["source"] == "hackernews"
        assert isinstance(normalized[0]["published_at"], datetime)
        assert normalized[0]["raw"] == raw_results[0]

    def test_self_post_with_text(self):
        """Test normalization of HN self-post (Ask HN, Show HN)."""
        raw_results = [
            {
                "id": 12345,
                "title": "Ask HN: Best practices?",
                "text": "I'm wondering about best practices for...",
                "time": 1704067200,
            }
        ]

        normalized = normalize_hackernews(raw_results)

        assert len(normalized) == 1
        assert normalized[0]["url"] == "https://news.ycombinator.com/item?id=12345"
        assert normalized[0]["summary"] == "I'm wondering about best practices for..."

    def test_missing_title_skipped(self):
        """Test that results without title are skipped."""
        raw_results = [{"id": 123, "url": "https://example.com", "time": 1704067200}]

        normalized = normalize_hackernews(raw_results)

        assert len(normalized) == 0

    def test_missing_url_and_text_skipped(self):
        """Test that results without URL and text are skipped."""
        raw_results = [{"id": 123, "title": "Article", "time": 1704067200}]

        normalized = normalize_hackernews(raw_results)

        assert len(normalized) == 0

    def test_text_truncation(self):
        """Test that long text is truncated to 500 chars."""
        long_text = "b" * 600
        raw_results = [{"id": 123, "title": "Ask HN", "text": long_text, "time": 1704067200}]

        normalized = normalize_hackernews(raw_results)

        assert len(normalized[0]["summary"]) == 500

    def test_published_at_none_when_missing(self):
        """Test that published_at is None when time not provided."""
        raw_results = [{"id": 123, "title": "Article", "url": "https://example.com"}]

        normalized = normalize_hackernews(raw_results)

        assert normalized[0]["published_at"] is None

    def test_empty_input(self):
        """Test handling of empty input list."""
        normalized = normalize_hackernews([])

        assert normalized == []

    def test_invalid_input_type(self):
        """Test that non-list input raises ValueError."""
        with pytest.raises(ValueError, match="must be a list"):
            normalize_hackernews({"not": "a list"})


class TestNormalizeArxiv:
    """Tests for arXiv result normalization."""

    def test_valid_input(self):
        """Test normalization of valid arXiv results."""
        raw_results = [
            {
                "entry_id": "http://arxiv.org/abs/2401.00001v1",
                "title": "Novel Approach to Machine Learning",
                "summary": "We present a novel approach to...",
                "published": "2024-01-15T10:00:00+00:00",
                "authors": ["John Doe", "Jane Smith"],
            }
        ]

        normalized = normalize_arxiv(raw_results)

        assert len(normalized) == 1
        assert normalized[0]["title"] == "Novel Approach to Machine Learning"
        assert normalized[0]["url"] == "http://arxiv.org/abs/2401.00001v1"
        assert normalized[0]["summary"] == "We present a novel approach to..."
        assert normalized[0]["source"] == "arxiv"
        assert isinstance(normalized[0]["published_at"], datetime)
        assert normalized[0]["raw"] == raw_results[0]

    def test_missing_title_skipped(self):
        """Test that results without title are skipped."""
        raw_results = [{"entry_id": "http://arxiv.org/abs/2401.00001", "summary": "Summary"}]

        normalized = normalize_arxiv(raw_results)

        assert len(normalized) == 0

    def test_missing_entry_id_skipped(self):
        """Test that results without entry_id are skipped."""
        raw_results = [{"title": "Paper Title", "summary": "Summary"}]

        normalized = normalize_arxiv(raw_results)

        assert len(normalized) == 0

    def test_summary_truncation(self):
        """Test that long summaries are truncated to 500 chars."""
        long_summary = "c" * 600
        raw_results = [
            {
                "entry_id": "http://arxiv.org/abs/2401.00001",
                "title": "Paper",
                "summary": long_summary,
            }
        ]

        normalized = normalize_arxiv(raw_results)

        assert len(normalized[0]["summary"]) == 500

    def test_published_at_none_when_missing(self):
        """Test that published_at is None when not provided."""
        raw_results = [
            {
                "entry_id": "http://arxiv.org/abs/2401.00001",
                "title": "Paper",
                "summary": "Summary",
            }
        ]

        normalized = normalize_arxiv(raw_results)

        assert normalized[0]["published_at"] is None

    def test_empty_input(self):
        """Test handling of empty input list."""
        normalized = normalize_arxiv([])

        assert normalized == []

    def test_invalid_input_type(self):
        """Test that non-list input raises ValueError."""
        with pytest.raises(ValueError, match="must be a list"):
            normalize_arxiv(123)


class TestNormalizeGithubTrending:
    """Tests for GitHub Trending result normalization."""

    def test_valid_input(self):
        """Test normalization of valid GitHub Trending results."""
        raw_results = [
            {
                "name": "username/repo-name",
                "url": "https://github.com/username/repo-name",
                "description": "An awesome repository for...",
                "stars": "1,234",
                "language": "Python",
            }
        ]

        normalized = normalize_github_trending(raw_results)

        assert len(normalized) == 1
        assert normalized[0]["title"] == "username/repo-name"
        assert normalized[0]["url"] == "https://github.com/username/repo-name"
        assert normalized[0]["summary"] == "An awesome repository for..."
        assert normalized[0]["source"] == "github"
        assert normalized[0]["published_at"] is None
        assert normalized[0]["raw"] == raw_results[0]

    def test_missing_name_skipped(self):
        """Test that results without name are skipped."""
        raw_results = [{"url": "https://github.com/user/repo", "description": "Description"}]

        normalized = normalize_github_trending(raw_results)

        assert len(normalized) == 0

    def test_missing_url_skipped(self):
        """Test that results without URL are skipped."""
        raw_results = [{"name": "user/repo", "description": "Description"}]

        normalized = normalize_github_trending(raw_results)

        assert len(normalized) == 0

    def test_description_truncation(self):
        """Test that long descriptions are truncated to 500 chars."""
        long_description = "d" * 600
        raw_results = [
            {
                "name": "user/repo",
                "url": "https://github.com/user/repo",
                "description": long_description,
            }
        ]

        normalized = normalize_github_trending(raw_results)

        assert len(normalized[0]["summary"]) == 500

    def test_empty_description(self):
        """Test handling of empty description."""
        raw_results = [
            {
                "name": "user/repo",
                "url": "https://github.com/user/repo",
                "description": "",
            }
        ]

        normalized = normalize_github_trending(raw_results)

        assert normalized[0]["summary"] == ""

    def test_empty_input(self):
        """Test handling of empty input list."""
        normalized = normalize_github_trending([])

        assert normalized == []

    def test_invalid_input_type(self):
        """Test that non-list input raises ValueError."""
        with pytest.raises(ValueError, match="must be a list"):
            normalize_github_trending("invalid")


class TestNormalizeGoogleTrends:
    """Tests for Google Trends result normalization."""

    def test_valid_input_single_keyword(self):
        """Test normalization of Google Trends with one keyword."""
        raw_results = {
            "keywords": ["AI"],
            "data": [
                {"date": "2024-01-01", "AI": 100},
                {"date": "2024-01-02", "AI": 95},
            ],
        }

        normalized = normalize_google_trends(raw_results)

        assert len(normalized) == 1
        assert normalized[0]["title"] == "Google Trends: AI"
        assert normalized[0]["url"] == "https://trends.google.com/trends/explore?q=AI"
        assert "Interest data for 'AI'" in normalized[0]["summary"]
        assert normalized[0]["source"] == "google_trends"
        assert normalized[0]["published_at"] is None
        assert normalized[0]["raw"] == raw_results

    def test_valid_input_multiple_keywords(self):
        """Test normalization creates one record per keyword."""
        raw_results = {
            "keywords": ["AI", "Machine Learning"],
            "data": [{"date": "2024-01-01", "AI": 100, "Machine Learning": 80}],
        }

        normalized = normalize_google_trends(raw_results)

        assert len(normalized) == 2
        assert normalized[0]["title"] == "Google Trends: AI"
        assert normalized[1]["title"] == "Google Trends: Machine Learning"
        assert normalized[1]["url"] == "https://trends.google.com/trends/explore?q=Machine+Learning"
        # Both records share the same raw payload
        assert normalized[0]["raw"] == raw_results
        assert normalized[1]["raw"] == raw_results

    def test_empty_keywords(self):
        """Test handling of empty keywords list."""
        raw_results = {"keywords": [], "data": []}

        normalized = normalize_google_trends(raw_results)

        assert normalized == []

    def test_missing_keywords_field(self):
        """Test handling when keywords field is missing."""
        raw_results = {"data": []}

        normalized = normalize_google_trends(raw_results)

        assert normalized == []

    def test_empty_keyword_skipped(self):
        """Test that empty/whitespace keywords are skipped."""
        raw_results = {"keywords": ["AI", "", "  ", "ML"], "data": []}

        normalized = normalize_google_trends(raw_results)

        assert len(normalized) == 2
        assert normalized[0]["title"] == "Google Trends: AI"
        assert normalized[1]["title"] == "Google Trends: ML"

    def test_keyword_url_encoding(self):
        """Test that keywords with spaces are URL-encoded."""
        raw_results = {"keywords": ["Generative AI"], "data": []}

        normalized = normalize_google_trends(raw_results)

        assert normalized[0]["url"] == "https://trends.google.com/trends/explore?q=Generative+AI"

    def test_invalid_input_type(self):
        """Test that non-dict input raises ValueError."""
        with pytest.raises(ValueError, match="must be a dict"):
            normalize_google_trends([])

    def test_invalid_input_type_list(self):
        """Test that list input raises ValueError."""
        with pytest.raises(ValueError, match="must be a dict"):
            normalize_google_trends(["keyword"])


class TestCanonicalSchema:
    """Tests to verify all normalizers follow the canonical schema."""

    def test_all_required_fields_present(self):
        """Test that all normalizers return records with required fields."""
        # Tavily
        tavily_result = normalize_tavily([{"title": "T", "url": "https://x.com", "content": "C"}])
        assert set(tavily_result[0].keys()) == {
            "title",
            "summary",
            "url",
            "source",
            "published_at",
            "raw",
        }

        # HackerNews
        hn_result = normalize_hackernews(
            [{"id": 1, "title": "T", "url": "https://x.com", "time": 1704067200}]
        )
        assert set(hn_result[0].keys()) == {
            "title",
            "summary",
            "url",
            "source",
            "published_at",
            "raw",
        }

        # arXiv
        arxiv_result = normalize_arxiv(
            [
                {
                    "title": "T",
                    "entry_id": "http://arxiv.org/abs/1",
                    "summary": "S",
                    "published": "2024-01-01T00:00:00Z",
                }
            ]
        )
        assert set(arxiv_result[0].keys()) == {
            "title",
            "summary",
            "url",
            "source",
            "published_at",
            "raw",
        }

        # GitHub
        github_result = normalize_github_trending(
            [{"name": "repo", "url": "https://github.com/r", "description": "D"}]
        )
        assert set(github_result[0].keys()) == {
            "title",
            "summary",
            "url",
            "source",
            "published_at",
            "raw",
        }

        # Google Trends
        trends_result = normalize_google_trends({"keywords": ["AI"], "data": []})
        assert set(trends_result[0].keys()) == {
            "title",
            "summary",
            "url",
            "source",
            "published_at",
            "raw",
        }

    def test_source_field_values(self):
        """Test that source field has correct hardcoded values."""
        assert (
            normalize_tavily([{"title": "T", "url": "https://x.com", "content": ""}])[0]["source"]
            == "tavily"
        )
        assert (
            normalize_hackernews([{"id": 1, "title": "T", "url": "https://x.com"}])[0]["source"]
            == "hackernews"
        )
        assert (
            normalize_arxiv([{"title": "T", "entry_id": "http://arxiv.org/abs/1", "summary": ""}])[
                0
            ]["source"]
            == "arxiv"
        )
        assert (
            normalize_github_trending(
                [{"name": "r", "url": "https://github.com/r", "description": ""}]
            )[0]["source"]
            == "github"
        )
        assert (
            normalize_google_trends({"keywords": ["AI"], "data": []})[0]["source"]
            == "google_trends"
        )
