from datetime import datetime
from typing import Any, Dict
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.main import app
from pytest_mock import MockerFixture
import httpx
from app.models.custom_types import CosmosAccountStatus, CosmosAPIType
from app.models.cosmos_models import CosmosAccountStatusResponse
from app.routers.cosmos_router import get_cosmos_manager

def test_create_cosmos_account_async(mocker: MockerFixture) -> None:
    """Test account creation endpoint initiastes async provisioning"""
    # ARRANGE: set up test conditioons and mocks
    #
    # Mock the azure integration class to prevent real API Calls

    mock_manager_class = mocker.patch(
        "app.routers.cosmos_router.AzureCosmosManager"
    )

    mock_async_method: mocker.AsyncMock = mocker.AsyncMock(
        return_value=CosmosAccountStatusResponse(
            account_name="test_account",
            status= CosmosAccountStatus.QUEUED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            message="Provisioning initiated",
        )
    )


    # Configure mock instance
    mock_manager_instance = mock_manager_class.return_value
    mock_manager_instance.create_account_async = mock_async_method

    #override fastapi dep
    app.dependency_overrides[get_cosmos_manager] = lambda: mock_manager_instance

    # initialize client
    client: TestClient = TestClient(app)

    # test payload

    test_payload: Dict[str, str] = {
        "account_name": "test_account",
        "location": "eastus",
        "api_type": "sql",
    }

    # Act: Make the request
    response: httpx.Response = client.post("/cosmos/create", json=test_payload)

    # Assert: Check the response
    assert response.status_code == 202

    # Check the response body
    response_data: Dict[str, Any] = response.json()
    assert response_data["account_name"] == "test_account"
    assert response_data["status"] == CosmosAccountStatus.QUEUED

    # Verify async method was called with correct parameters
    mock_async_method.assert_awaited_once_with(
        account_name="test_account",
        location="eastus",
        api_type=   CosmosAPIType.SQL
    )

    # Cleanup: Reset dependency overrides
    app.dependency_overrides.clear()

