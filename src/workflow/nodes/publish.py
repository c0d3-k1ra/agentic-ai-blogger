"""PublishNode - Persists reviewed article to database.

Integrates database layer into the LangGraph workflow.
"""

from datetime import datetime, timezone

from src.database.db import create_article, create_topic, get_session, get_topic_by_name
from src.workflow.nodes import BaseNode, NodeRegistry, handle_node_errors, log_node_execution


@NodeRegistry.register("publish")
class PublishNode(BaseNode):
    """Workflow node that persists reviewed article to database."""

    @property
    def name(self) -> str:
        """Return node identifier."""
        return "publish"

    @handle_node_errors
    @log_node_execution
    async def execute(self, state: dict) -> dict:
        """Persist reviewed article to database.

        Args:
            state: Workflow state containing:
                - reviewed_article: ReviewedArticle with polished content and metadata
                - selected_topic: The article topic
                - article_outline: The outline structure (for metadata)

        Returns:
            State updates with:
                - article_id: UUID of created article in database
                - published_at: Timestamp when article was published
                - current_step: Transition to "complete"
        """
        # Extract inputs
        reviewed_article = state.get("reviewed_article")
        topic_name = state.get("selected_topic")
        outline = state.get("article_outline")

        # Validate inputs
        if reviewed_article is None:
            raise ValueError("reviewed_article is required")

        if not hasattr(reviewed_article, "polished_content"):
            raise ValueError("reviewed_article must have polished_content attribute")

        if not topic_name or not topic_name.strip():
            raise ValueError("selected_topic is required and cannot be empty")

        # Prepare metadata
        metadata = {
            "seo_title": reviewed_article.seo_title,
            "seo_subtitle": reviewed_article.seo_subtitle,
            "tags": list(reviewed_article.tags),
            "word_count": reviewed_article.word_count,
            "readability_score": reviewed_article.readability_score,
            "improvements_made": reviewed_article.improvements_made,
        }

        # Add outline info if available
        if outline is not None:
            metadata["outline"] = {
                "topic": outline.topic,
                "sections": [
                    {
                        "title": section.title,
                        "subsections": list(section.subsections),
                    }
                    for section in outline.sections
                ],
            }

        # Persist to database
        with get_session() as session:
            # Get or create topic
            topic = get_topic_by_name(session, topic_name)
            if topic is None:
                # Create new topic
                topic = create_topic(
                    session,
                    name=topic_name,
                    description=f"Articles about {topic_name}",
                    keywords=list(reviewed_article.tags),
                )

            # Create article with published status
            published_at = datetime.now(timezone.utc)
            article = create_article(
                session,
                topic_id=topic.id,
                title=reviewed_article.seo_title,
                content=reviewed_article.polished_content,
                metadata=metadata,
            )

            # Update article to published status
            article.status = "published"
            article.published_at = published_at
            session.flush()
            session.refresh(article)

            article_id = str(article.id)

        # Return state updates
        return {
            "article_id": article_id,
            "published_at": published_at.isoformat(),
            "current_step": "complete",
        }
