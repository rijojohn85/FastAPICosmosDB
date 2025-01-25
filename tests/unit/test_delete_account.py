import httpx
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from pytest_mock import MockerFixture

from app.main import app
from app.models.cosmos_models import CosmosAccountStatusResponse
from app.models.custom_types import CosmosAccountStatus
from app.routers.cosmos_router import get_cosmos_manager


def test_successful_delete_account_with_email()-> None:
    #Setup
    with (
        patch("app.routers.cosmos_router.AzureCosmosManager")   as mock_manager,
        patch("app.routers.cosmos_router.send_deletion_success_email") as mock_send_success,
        patch("app.routers.cosmos_router.send_deletion_failure_email") as mock_send_failure,
    ):

        mock_instance = mock_manager.return_value
        mock_instance.account_exists = AsyncMock(return_value=True)
        mock_instance.delete_account_async=AsyncMock()
        app.dependency_overrides[get_cosmos_manager]= lambda : mock_instance

    #Act

        client = TestClient(app)
        response: httpx.Response = client.delete("/cosmos/accounts/test_account")
        assert response.status_code == 204
        assert not response.content
        mock_instance.delete_account_async.assert_awaited_once_with("test_account")
        mock_send_failure.assert_not_called()
        mock_send_success.assert_called_once()

def test_unsuccessful_delete_account_with_email()-> None:
    #Setup
    with (
        patch("app.routers.cosmos_router.AzureCosmosManager")   as mock_manager,
        patch("app.routers.cosmos_router.send_success_notification") as mock_send_failure,
        patch("app.routers.cosmos_router.send_failure_notification") as mock_send_success,
    ):
        mock_instance = mock_manager.return_value
        mock_instance.account_exists = AsyncMock(return_value=False)
        mock_instance.delete_account_async = AsyncMock()

        app.dependency_overrides[get_cosmos_manager]= lambda : mock_instance
        #Act

        client = TestClient(app)
        response: httpx.Response = client.delete("/cosmos/accounts/failing-account")
        assert response.status_code == 404
        mock_send_success.assert_called_once()
        mock_instance.delete_account_async.assert_awaited_once_with("failing-account")
        mock_send_failure.assert_not_called()
