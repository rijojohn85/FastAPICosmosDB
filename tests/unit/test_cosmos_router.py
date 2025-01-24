from datetime import datetime
from typing import Any, Dict
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from pytest_mock import MockerFixture
import httpx
from app.models.custom_types import CosmosAccountStatus
from app.models.cosmos_models import CosmosAccountStatusResponse

def test_create_cosmos_account_async(mocker: MockerFixture) -> None:
    """Test account creation endpoint initiastes async provisioning"""
    # ARRANGE: set up test conditioons and mocks
    #
    # Mock the azure integration class to prevent real API Calls

    mock_cosmos_manager: MagicMock = mocker.patch(
        "app.routers.cosmos_router.AzureCosmosManager"
    )

    # Configure mock response
    mock_response = CosmosAccountStatusResponse(
        account_name="test-account",
        status=CosmosAccountStatus.QUEUED,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        message="Provisioning queued",
    )
    mock_cosmos_manager.return_value.test_create_cosmos_account_async.return_value = mock_response

    # initialize client
    client: TestClient = TestClient(app, backend="asyncio")

    # test payload

    test_payload: Dict[str, str] = {
        "account_name": "test-account",
        "location": "eastus",
        "api_type": "sql",
    }

    # Act: Make the request
    response: httpx.Response = client.post("/cosmos/create", json=test_payload)

    # Assert: Check the response
    assert response.status_code == 202

    # Check the response body
    response_data: Dict[str, Any] = response.json()
    assert response_data=={
        "message": "Account provisioning initiated",
        "status_endpoint": "/cosmos/status/test-account",
    }
    #mock call verification
    mock_cosmos_manager.return_value.create_account_async.assert_called_once_with(
        account_name=test_payload["account_name"], #str
        location=test_payload["location"], #str
        api_type=test_payload["api_type"],#Literal["sql", "mongo"]
    )

