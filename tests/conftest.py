"""Common test fixtures."""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_bedrock_response():
    """Mock Bedrock API response."""
    return {
        "stopReason": "end_turn",
        "content": [
            {"text": "I've turned on the light."}
        ]
    }
