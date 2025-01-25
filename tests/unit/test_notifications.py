import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import status
from httpx import Response

from app.main import app
from pytest_mock import MockFixture, MockerFixture
from app.models.cosmos_models import CosmosAPIType
from typing import Dict

client = TestClient(app)

@pytest.mark.asyncio
async def test_provisioning_failure_sends_email(mocker: MockerFixture):
    """
    Test that a provisioning failure triggers an email notification
    with proper error details
    """
    #Mock external dependencies
    mock_email: MagicMock= mocker.patch("app.services.gmail_sender.GmailSender.send")
    mock_manager: AsyncMock = AsyncMock()
    mock_manager.create_account_async.side_effect = Exception("Disk Full")

    #Simulate failed provisioning request
    with patch("app.routers.cosmos_router.AzureCosmosManager", return_value=mock_manager):
        response: Response = client.post(
            "/cosmos/create",
            json={
                "account_name": "test-account",
                "location" : "Central India",
                "api_type": CosmosAPIType.SQL
            }
        )

    status_code: int = response.status_code
    response_data: dict[str,str] = response.json()

    assert status_code == status.HTTP_202_ACCEPTED
    assert response_data["status"]=="queued"

    #Verify email parameters with type checks
    email_recipient: str = mock_email.call_args[1]["recipient"]
    email_subject: str = mock_email.call_args[1]["subject"]
    email_message: str = mock_email.call_args[1]["message"]

    assert email_recipient == "admin@company.com" #incorrect recipient
    assert "Provisioning failed" in email_subject
    assert "Disk Full" in email_message


