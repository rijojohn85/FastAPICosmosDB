from typing import Any, Dict
from fastapi.testclient import TestClient

from app.core.config.settings import get_settings
from app.main import app
from unittest.mock import patch, AsyncMock
import httpx
from app.models.custom_types import CosmosAccountStatus, CosmosAPIType
from app.routers.cosmos_router import get_cosmos_manager
from app.services.status_tracker import StatusTracker

def test_create_cosmos_account_async() -> None:
    """Test account creation endpoint initiates async provisioning"""
    # ARRANGE: set up test conditions and mocks
    #
    # Mock the azure integration class to prevent real API Calls
    with (
        patch("app.routers.cosmos_router.AzureCosmosManager")   as mock_manager_class,
        patch("app.core.config.settings.get_settings") as mock_settings_function

    ):

        mock_async_method: AsyncMock =AsyncMock()


        # Configure mock instance
        mock_manager_instance = mock_manager_class.return_value
        mock_manager_instance.create_account_async = mock_async_method

        #override fastapi dep
        app.dependency_overrides[get_cosmos_manager] = lambda: mock_manager_instance
        app.dependency_overrides[get_settings] = lambda: mock_settings_function

        # initialize client
        client: TestClient = TestClient(app)

        # test payload

        test_payload: Dict[str, str] = {
            "account_name": "test-account",
            "location": "Central India",
            "api_type": "sql",
        }

        # Act: Make the request
        response: httpx.Response = client.post("/cosmos/accounts", json=test_payload)

        # Assert: Check the response
        assert response.status_code == 202

        # Check the response body
        response_data: Dict[str, Any] = response.json()
        assert response_data["account_name"] == "test-account"
        assert response_data["status"] == CosmosAccountStatus.QUEUED

        # Verify async method was called with correct parameters
        mock_async_method.assert_awaited_once_with(
            account_name="test-account",
            location="Central India",
            api_type=   CosmosAPIType.SQL
        )

        # Cleanup: Reset dependency overrides
        app.dependency_overrides.clear()

def test_get_provisioning_status_success() -> None:
    """Test successful status retrieval"""
    # Setup
    test_account = "test-account-123"
    StatusTracker.update_status(
        test_account,
        CosmosAccountStatus.IN_PROGRESS,
        "Provisioning in progress"
    )

    client: TestClient = TestClient(app)
    # Execute
    response = client.get(f"/cosmos/accounts/{test_account}")

    # Verify
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    # Cleanup
    StatusTracker._statues.clear()

def test_get_provisioning_status_not_found() -> None:
    """Test status check for non-existent account"""
    client: TestClient = TestClient(app)
    response = client.get("/cosmos/accounts/non-existent")

    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "ACCOUNT_NOT_FOUND"

