"""Tests for config flow validation."""
import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import NoCredentialsError

from homeassistant.core import HomeAssistant

from custom_components.bedrock_conversation.config_flow import validate_aws_credentials


@pytest.mark.asyncio
async def test_validate_credentials_success(hass: HomeAssistant):
    """Test successful credential validation."""
    with patch("boto3.client") as mock_boto:
        mock_bedrock = MagicMock()
        mock_bedrock.list_foundation_models = MagicMock(return_value={"modelSummaries": []})
        mock_boto.return_value = mock_bedrock
        
        result = await validate_aws_credentials(
            hass,
            "us-east-1",
            "test_key",
            "test_secret"
        )
        
        assert result is None


@pytest.mark.asyncio
async def test_validate_credentials_invalid(hass: HomeAssistant):
    """Test invalid credential validation."""
    with patch("boto3.client") as mock_boto:
        mock_boto.side_effect = NoCredentialsError()
        
        result = await validate_aws_credentials(
            hass,
            "us-east-1",
            "bad_key",
            "bad_secret"
        )
        
        assert result == {"base": "invalid_credentials"}
