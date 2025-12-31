"""CLI helper functions for user interaction in workflow.

This module provides utilities for displaying information and collecting user input
during workflow execution. Used by interrupt nodes to pause and gather decisions.
"""

from typing import Literal, Optional


def display_topics_for_selection(scored_topics: list[dict]) -> None:
    """Display scored topics in a formatted list for user selection.

    Args:
        scored_topics: List of topics with scores from AnalyzeTrendsNode

    Example Output:
        Available Topics (sorted by relevance):
        1. [Score: 8.5] Python Async Programming Best Practices
        2. [Score: 7.2] Modern Python Type Hints Guide
        3. [Score: 6.8] FastAPI vs Flask Comparison
    """
    if not scored_topics:
        print("\n⚠️  No topics available for selection")
        return

    print("\n" + "=" * 70)
    print("📊 AVAILABLE TOPICS (sorted by relevance)")
    print("=" * 70)

    for idx, topic_data in enumerate(scored_topics, start=1):
        topic = topic_data.get("topic", "Unknown")
        score = topic_data.get("score", 0.0)
        reasoning = topic_data.get("reasoning", "")

        print(f"\n{idx}. [Score: {score:.1f}] {topic}")
        if reasoning:
            # Truncate long reasoning
            short_reasoning = reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
            print(f"   💡 {short_reasoning}")

    print("\n" + "=" * 70)


def prompt_user_topic_selection(num_topics: int) -> int:
    """Prompt user to select a topic by number.

    Args:
        num_topics: Total number of topics available

    Returns:
        Selected topic index (1-based)

    Raises:
        ValueError: If user input is invalid
    """
    while True:
        try:
            choice = input(f"\n👉 Select a topic (1-{num_topics}): ").strip()

            if not choice:
                print("❌ Please enter a number")
                continue

            choice_num = int(choice)

            if 1 <= choice_num <= num_topics:
                return choice_num

            print(f"❌ Please enter a number between 1 and {num_topics}")

        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n\n⚠️  Selection cancelled")
            raise


def display_article_for_review(reviewed_article: dict) -> None:
    """Display reviewed article with metadata for user review.

    Args:
        reviewed_article: Article data from ReviewNode

    Example Output:
        Article Preview:
        Title: Python Async Programming Best Practices
        Subtitle: Master asynchronous programming in Python
        Tags: python, async, programming
        Word Count: 1500
        Readability: 65.2

        [Article content preview...]
    """
    print("\n" + "=" * 70)
    print("📄 ARTICLE REVIEW")
    print("=" * 70)

    # Display metadata
    seo_title = reviewed_article.get("seo_title", "No title")
    seo_subtitle = reviewed_article.get("seo_subtitle", "No subtitle")
    tags = reviewed_article.get("tags", [])
    word_count = reviewed_article.get("word_count", 0)
    readability_score = reviewed_article.get("readability_score", 0.0)

    print(f"\n📌 Title: {seo_title}")
    print(f"📝 Subtitle: {seo_subtitle}")
    print(f"🏷️  Tags: {', '.join(tags)}")
    print(f"📊 Word Count: {word_count}")
    print(f"📈 Readability Score: {readability_score:.1f}")

    # Display article content (truncated)
    polished_content = reviewed_article.get("polished_content", "")
    if polished_content:
        preview_length = 500
        content_preview = polished_content[:preview_length]
        if len(polished_content) > preview_length:
            content_preview += "..."

        print("\n" + "-" * 70)
        print("CONTENT PREVIEW:")
        print("-" * 70)
        print(content_preview)
        print("-" * 70)

        if len(polished_content) > preview_length:
            print(f"\n(Showing first {preview_length} characters of {len(polished_content)} total)")

    print("\n" + "=" * 70)


def prompt_user_approval() -> tuple[Literal["approve", "revise"], Optional[str]]:
    """Prompt user to approve article or request revision.

    Returns:
        Tuple of (decision, feedback) where:
        - decision: "approve" or "revise"
        - feedback: User's revision feedback (None if approved)

    Raises:
        KeyboardInterrupt: If user cancels
    """
    print("\n" + "=" * 70)
    print("🔍 ARTICLE APPROVAL")
    print("=" * 70)
    print("\nOptions:")
    print("  1. Approve - Proceed to publish")
    print("  2. Revise - Request changes with feedback")
    print("=" * 70)

    while True:
        try:
            choice = input("\n👉 Enter your choice (1 or 2): ").strip()

            if choice == "1":
                confirm = input("\n✅ Confirm approval? (yes/no): ").strip().lower()
                if confirm in ("yes", "y"):
                    print("\n✅ Article approved for publication!")
                    return "approve", None
                print("❌ Approval cancelled")
                continue

            elif choice == "2":
                print("\n📝 Please provide revision feedback:")
                print("(Describe what changes you'd like to see)")
                feedback = input("\n👉 Feedback: ").strip()

                if not feedback:
                    print("❌ Feedback cannot be empty")
                    continue

                confirm = input("\n✅ Confirm revision request? (yes/no): ").strip().lower()
                if confirm in ("yes", "y"):
                    print("\n✅ Revision requested!")
                    return "revise", feedback
                print("❌ Revision cancelled")
                continue

            else:
                print("❌ Please enter 1 or 2")

        except KeyboardInterrupt:
            print("\n\n⚠️  Review cancelled")
            raise


def display_error(message: str) -> None:
    """Display error message in formatted style.

    Args:
        message: Error message to display
    """
    print("\n" + "=" * 70)
    print("❌ ERROR")
    print("=" * 70)
    print(f"\n{message}")
    print("\n" + "=" * 70)


def display_info(message: str) -> None:
    """Display informational message in formatted style.

    Args:
        message: Info message to display
    """
    print("\n" + "=" * 70)
    print("ℹ️  INFO")
    print("=" * 70)
    print(f"\n{message}")
    print("\n" + "=" * 70)


def display_success(message: str) -> None:
    """Display success message in formatted style.

    Args:
        message: Success message to display
    """
    print("\n" + "=" * 70)
    print("✅ SUCCESS")
    print("=" * 70)
    print(f"\n{message}")
    print("\n" + "=" * 70)
