
"""Test fixtures for bedrock_conversation."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_setup_entry():
    """Mock setting up a config entry."""
    return AsyncMock(return_value=True)


@pytest.fixture
def mock_unload_entry():
    """Mock unloading a config entry."""
    return AsyncMock(return_value=True)


# Disable autouse hass fixture by providing our own version that doesn't depend on pytest-asyncio
@pytest.fixture
def hass():
    """Mock Home Assistant fixture that's synchronous."""
    mock_hass = MagicMock()
    mock_hass.data = {}
    mock_hass.services = MagicMock()
    mock_hass.states = MagicMock()
    mock_hass.config = {}
    mock_hass.loop = None  # Avoid asyncio related issues
    
    # Make async methods return completed futures
    mock_hass.async_add_executor_job = AsyncMock()
    mock_hass.async_create_task = AsyncMock()
    
    return mock_hass
