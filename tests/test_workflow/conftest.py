"""Pytest configuration for workflow tests.

This module ensures all workflow nodes are imported and registered
before tests run. This is necessary because the node registration
happens via decorators when modules are imported.
"""

import pytest

# Import all node modules to trigger registration
# This must happen before any tests that check node registration
from src.workflow.nodes import (  # noqa: F401
    analyze_trends,
    plan_structure,
    publish,
    research,
    review,
    revision,
    scout_topics,
    user_interaction,
    write_draft,
)


@pytest.fixture(autouse=True)
def ensure_nodes_registered():
    """Fixture to ensure nodes are registered before each test.

    This fixture runs automatically before each test to ensure
    all nodes are properly registered in the NodeRegistry.
    """
    # Nodes are already registered by the imports above
    # This fixture just ensures the imports have happened
    yield
