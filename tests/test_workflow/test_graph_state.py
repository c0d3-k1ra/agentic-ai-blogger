"""Tests for LangGraph state schema.

Tests cover:
- State creation with required fields
- State creation with optional fields
- Validation helpers
- Initial state creation
- Edge cases and error handling
"""

import pytest

from src.workflow.graph_state import (
    ArticleWorkflowState,
    WorkflowStep,
    create_initial_state,
    validate_required_fields,
    validate_revision_count,
    validate_workflow_step,
)


class TestArticleWorkflowState:
    """Tests for ArticleWorkflowState TypedDict."""

    def test_state_creation_with_required_fields_only(self):
        """Test state creation with only required fields."""
        state: ArticleWorkflowState = {
            "workflow_id": "test-123",
            "user_query": "Python async programming",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        assert state["workflow_id"] == "test-123"
        assert state["user_query"] == "Python async programming"
        assert state["current_step"] == "scout_topics"
        assert state["revision_count"] == 0
        assert state["max_revisions"] == 3
        assert state["errors"] == []
        assert state["retry_count"] == 0

    def test_state_creation_with_all_fields(self):
        """Test state creation with all possible fields."""
        state: ArticleWorkflowState = {
            # Required fields
            "workflow_id": "test-456",
            "user_query": "Machine Learning",
            "current_step": "review_article",
            "revision_count": 1,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
            # Optional user inputs
            "selected_topic": "Deep Learning Fundamentals",
            "user_feedback": "Add more examples",
            "user_approval": False,
            # Optional agent outputs
            "topic_candidates": [{"topic": "ML Basics", "score": 0.9}],
            "scored_topics": [{"topic": "ML Basics", "score": 0.95}],
            "outline": {"title": "ML Guide", "sections": []},
            "research_dossiers": {"intro": {"sources": []}},
            "written_sections": {"intro": {"content": "# Intro"}},
            "reviewed_article": {"polished_content": "# Article"},
            "revised_article": {"content": "# Revised"},
            # Optional metadata
            "article_id": "art-789",
            "topic_id": "topic-101",
            "final_article": {"content": "# Final"},
        }

        # Verify required fields
        assert state["workflow_id"] == "test-456"
        assert state["user_query"] == "Machine Learning"
        assert state["current_step"] == "review_article"

        # Verify optional user inputs
        assert state["selected_topic"] == "Deep Learning Fundamentals"
        assert state["user_feedback"] == "Add more examples"
        assert state["user_approval"] is False

        # Verify optional agent outputs
        assert len(state["topic_candidates"]) == 1
        assert state["outline"]["title"] == "ML Guide"

        # Verify optional metadata
        assert state["article_id"] == "art-789"
        assert state["topic_id"] == "topic-101"

    def test_state_with_accumulated_errors(self):
        """Test state with multiple errors accumulated."""
        state: ArticleWorkflowState = {
            "workflow_id": "test-789",
            "user_query": "Test query",
            "current_step": "failed",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [
                "LLM call failed",
                "Network timeout",
                "Retry exhausted",
            ],
            "retry_count": 3,
        }

        assert len(state["errors"]) == 3
        assert "LLM call failed" in state["errors"]
        assert state["retry_count"] == 3

    def test_state_partial_fields(self):
        """Test state with some optional fields populated."""
        state: ArticleWorkflowState = {
            "workflow_id": "test-partial",
            "user_query": "Partial test",
            "current_step": "plan_structure",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
            "selected_topic": "Selected Topic",
            # Other optional fields not provided
        }

        assert state["selected_topic"] == "Selected Topic"
        assert "user_feedback" not in state
        assert "outline" not in state


class TestWorkflowStepType:
    """Tests for WorkflowStep Literal type."""

    def test_valid_workflow_steps(self):
        """Test all valid workflow step values."""
        valid_steps: list[WorkflowStep] = [
            "scout_topics",
            "analyze_trends",
            "get_user_selection",
            "plan_structure",
            "research_sections",
            "write_sections",
            "review_article",
            "get_user_approval",
            "revise_article",
            "save_article",
            "completed",
            "failed",
        ]

        for step in valid_steps:
            state: ArticleWorkflowState = {
                "workflow_id": "test",
                "user_query": "test",
                "current_step": step,
                "revision_count": 0,
                "max_revisions": 3,
                "errors": [],
                "retry_count": 0,
            }
            assert state["current_step"] == step


class TestValidateRequiredFields:
    """Tests for validate_required_fields helper."""

    def test_all_required_fields_present(self):
        """Test validation with all required fields."""
        state = {
            "workflow_id": "test-123",
            "user_query": "Test query",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        is_valid, missing = validate_required_fields(state)

        assert is_valid is True
        assert missing == []

    def test_missing_single_required_field(self):
        """Test validation with one missing field."""
        state = {
            "workflow_id": "test-123",
            "user_query": "Test query",
            # Missing current_step
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
        }

        is_valid, missing = validate_required_fields(state)

        assert is_valid is False
        assert "current_step" in missing
        assert len(missing) == 1

    def test_missing_multiple_required_fields(self):
        """Test validation with multiple missing fields."""
        state = {
            "workflow_id": "test-123",
            # Missing: user_query, current_step, revision_count, max_revisions, errors, retry_count
        }

        is_valid, missing = validate_required_fields(state)

        assert is_valid is False
        assert len(missing) == 6
        assert "user_query" in missing
        assert "current_step" in missing
        assert "revision_count" in missing
        assert "max_revisions" in missing
        assert "errors" in missing
        assert "retry_count" in missing

    def test_empty_state(self):
        """Test validation with empty state."""
        state = {}

        is_valid, missing = validate_required_fields(state)

        assert is_valid is False
        assert len(missing) == 7  # All required fields missing

    def test_extra_fields_allowed(self):
        """Test validation allows extra optional fields."""
        state = {
            "workflow_id": "test-123",
            "user_query": "Test query",
            "current_step": "scout_topics",
            "revision_count": 0,
            "max_revisions": 3,
            "errors": [],
            "retry_count": 0,
            # Extra optional fields
            "selected_topic": "Extra field",
            "outline": {"title": "Test"},
        }

        is_valid, missing = validate_required_fields(state)

        assert is_valid is True
        assert missing == []


class TestValidateWorkflowStep:
    """Tests for validate_workflow_step helper."""

    def test_valid_steps(self):
        """Test all valid workflow steps."""
        valid_steps = [
            "scout_topics",
            "analyze_trends",
            "get_user_selection",
            "plan_structure",
            "research_sections",
            "write_sections",
            "review_article",
            "get_user_approval",
            "revise_article",
            "save_article",
            "completed",
            "failed",
        ]

        for step in valid_steps:
            assert validate_workflow_step(step) is True

    def test_invalid_steps(self):
        """Test invalid workflow steps."""
        invalid_steps = [
            "invalid_step",
            "unknown",
            "Scout_Topics",  # Wrong case
            "scout-topics",  # Wrong separator
            "",
            "  ",
            "123",
        ]

        for step in invalid_steps:
            assert validate_workflow_step(step) is False

    def test_empty_step(self):
        """Test empty string step."""
        assert validate_workflow_step("") is False

    def test_whitespace_step(self):
        """Test whitespace-only step."""
        assert validate_workflow_step("   ") is False


class TestValidateRevisionCount:
    """Tests for validate_revision_count helper."""

    def test_valid_revision_count_zero(self):
        """Test valid revision count at zero."""
        state = {"revision_count": 0, "max_revisions": 3}

        is_valid, error = validate_revision_count(state)

        assert is_valid is True
        assert error == ""

    def test_valid_revision_count_within_limit(self):
        """Test valid revision count within max."""
        state = {"revision_count": 2, "max_revisions": 3}

        is_valid, error = validate_revision_count(state)

        assert is_valid is True
        assert error == ""

    def test_valid_revision_count_at_limit(self):
        """Test valid revision count at max."""
        state = {"revision_count": 3, "max_revisions": 3}

        is_valid, error = validate_revision_count(state)

        assert is_valid is True
        assert error == ""

    def test_invalid_negative_revision_count(self):
        """Test invalid negative revision count."""
        state = {"revision_count": -1, "max_revisions": 3}

        is_valid, error = validate_revision_count(state)

        assert is_valid is False
        assert "cannot be negative" in error

    def test_invalid_zero_max_revisions(self):
        """Test invalid zero max revisions."""
        state = {"revision_count": 0, "max_revisions": 0}

        is_valid, error = validate_revision_count(state)

        assert is_valid is False
        assert "must be at least 1" in error

    def test_invalid_negative_max_revisions(self):
        """Test invalid negative max revisions."""
        state = {"revision_count": 0, "max_revisions": -1}

        is_valid, error = validate_revision_count(state)

        assert is_valid is False
        assert "must be at least 1" in error

    def test_invalid_count_exceeds_max(self):
        """Test revision count exceeds max."""
        state = {"revision_count": 5, "max_revisions": 3}

        is_valid, error = validate_revision_count(state)

        assert is_valid is False
        assert "exceeds max_revisions" in error
        assert "(5)" in error  # Shows actual count
        assert "(3)" in error  # Shows max

    def test_missing_revision_count_defaults_to_zero(self):
        """Test missing revision_count defaults to 0."""
        state = {"max_revisions": 3}

        is_valid, error = validate_revision_count(state)

        assert is_valid is True
        assert error == ""

    def test_missing_max_revisions_defaults_to_three(self):
        """Test missing max_revisions defaults to 3."""
        state = {"revision_count": 2}

        is_valid, error = validate_revision_count(state)

        assert is_valid is True
        assert error == ""


class TestCreateInitialState:
    """Tests for create_initial_state helper."""

    def test_create_initial_state_minimal(self):
        """Test creating initial state with minimal args."""
        state = create_initial_state("wf-123", "Python async")

        assert state["workflow_id"] == "wf-123"
        assert state["user_query"] == "Python async"
        assert state["current_step"] == "scout_topics"
        assert state["revision_count"] == 0
        assert state["max_revisions"] == 3  # Default
        assert state["errors"] == []
        assert state["retry_count"] == 0

    def test_create_initial_state_custom_max_revisions(self):
        """Test creating initial state with custom max revisions."""
        state = create_initial_state("wf-456", "ML basics", max_revisions=5)

        assert state["workflow_id"] == "wf-456"
        assert state["user_query"] == "ML basics"
        assert state["max_revisions"] == 5

    def test_create_initial_state_strips_whitespace(self):
        """Test that workflow_id and query are stripped."""
        state = create_initial_state("  wf-789  ", "  Test query  ")

        assert state["workflow_id"] == "wf-789"
        assert state["user_query"] == "Test query"

    def test_create_initial_state_empty_workflow_id(self):
        """Test error with empty workflow_id."""
        with pytest.raises(ValueError, match="workflow_id cannot be empty"):
            create_initial_state("", "Test query")

    def test_create_initial_state_whitespace_workflow_id(self):
        """Test error with whitespace-only workflow_id."""
        with pytest.raises(ValueError, match="workflow_id cannot be empty"):
            create_initial_state("   ", "Test query")

    def test_create_initial_state_empty_query(self):
        """Test error with empty query."""
        with pytest.raises(ValueError, match="user_query cannot be empty"):
            create_initial_state("wf-123", "")

    def test_create_initial_state_whitespace_query(self):
        """Test error with whitespace-only query."""
        with pytest.raises(ValueError, match="user_query cannot be empty"):
            create_initial_state("wf-123", "   ")

    def test_create_initial_state_invalid_max_revisions_zero(self):
        """Test error with max_revisions = 0."""
        with pytest.raises(ValueError, match="max_revisions must be at least 1"):
            create_initial_state("wf-123", "Test", max_revisions=0)

    def test_create_initial_state_invalid_max_revisions_negative(self):
        """Test error with negative max_revisions."""
        with pytest.raises(ValueError, match="max_revisions must be at least 1"):
            create_initial_state("wf-123", "Test", max_revisions=-1)

    def test_create_initial_state_max_revisions_one(self):
        """Test creating state with max_revisions = 1."""
        state = create_initial_state("wf-123", "Test", max_revisions=1)

        assert state["max_revisions"] == 1

    def test_create_initial_state_large_max_revisions(self):
        """Test creating state with large max_revisions."""
        state = create_initial_state("wf-123", "Test", max_revisions=100)

        assert state["max_revisions"] == 100

    def test_create_initial_state_validates_required_fields(self):
        """Test that created state passes validation."""
        state = create_initial_state("wf-123", "Test query")

        is_valid, missing = validate_required_fields(state)

        assert is_valid is True
        assert missing == []

    def test_create_initial_state_validates_revision_count(self):
        """Test that created state passes revision validation."""
        state = create_initial_state("wf-123", "Test query")

        is_valid, error = validate_revision_count(state)

        assert is_valid is True
        assert error == ""
