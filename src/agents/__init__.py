"""Agent modules for content generation.

This package contains intelligent agents for various content generation tasks.
"""

from src.agents.researcher import ResearchDossier, research_section
from src.agents.reviewer import ReviewedArticle, review_article
from src.agents.revision import RevisedArticle, revise_article
from src.agents.structure_planner import Outline, Section, generate_outline
from src.agents.topic_scout import generate_topics
from src.agents.trend_analyzer import ScoredTopic, analyze_trends
from src.agents.writer import WrittenSection, write_section

__all__ = [
    "generate_topics",
    "analyze_trends",
    "ScoredTopic",
    "generate_outline",
    "Outline",
    "Section",
    "research_section",
    "ResearchDossier",
    "write_section",
    "WrittenSection",
    "review_article",
    "ReviewedArticle",
    "revise_article",
    "RevisedArticle",
]
