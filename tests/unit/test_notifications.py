import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import status
from httpx import Response

from pytest_mock import MockFixture, MockerFixture
from app.models.cosmos_models import CosmosAPIType, CosmosAccountStatusResponse

from app.models.custom_types import CosmosAccountStatus


@pytest.mark.asyncio
async def test_provisioning_failure_sends_email(mocker: MockerFixture, client: TestClient)->None:
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
    call_kwargs = mock_email.call_args.kwargs

    assert call_kwargs["to"]== "rijo.john@infracloud.io" #incorrect recipient
    assert "Provisioning failed" in call_kwargs["subject"]
    assert "Disk Full" in call_kwargs["body"]

@pytest.mark.asyncio
async def test_provisioning_success_sends_email(mocker: MockerFixture, client: TestClient):
    """Test successful provisioning triggers confirmation email"""
    # Mock external dependencies
    mock_email = mocker.patch("app.services.gmail_sender.GmailSender.send")
    mock_manager = AsyncMock()

    # Simulate successful provisioning
    mock_manager.create_account_async.return_value = CosmosAccountStatusResponse(
        account_name="success-account",
        status=CosmosAccountStatus.QUEUED,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        message="Provisioning started"
    )

    with patch("app.routers.cosmos_router.AzureCosmosManager", return_value=mock_manager):
        response = client.post(
            "/cosmos/create",
            json={
                "account_name": "success-account",
                "location": "Central India",
                "api_type": "sql"
            }
        )

    # Verify email parameters
    mock_email.assert_called_once()
    call_kwargs = mock_email.call_args.kwargs
    assert call_kwargs["to"] == "rijo.john@infracloud.io"
    assert "cosmos db account ready" in call_kwargs["subject"].lower()
    assert "success-account" in call_kwargs["body"]
    assert "sql" in call_kwargs["body"]


