from sys import exception

import httpx
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
from app.routers.cosmos_router import get_cosmos_manager
from app.services.logging_service import logger


def test_successful_delete_account_with_email()-> None:
    #Setup
    with (
        patch("app.routers.cosmos_router.AzureCosmosManager")   as mock_manager,
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
        app.dependency_overrides.clear()

def test_unsuccessful_delete_account_with_email()-> None:
    #Setup
    with (
        patch("app.routers.cosmos_router.AzureCosmosManager")   as mock_manager,
        patch("app.routers.cosmos_router.send_deletion_failure_email") as mock_email,
    ):
        mock_instance = mock_manager.return_value
        mock_instance.account_exists = AsyncMock(return_value=False)
        mock_instance.delete_account_async.side_effect=ValueError("Account does not exist")
        app.dependency_overrides[get_cosmos_manager]= lambda : mock_instance

        #Act

        client = TestClient(app)
        response: httpx.Response = client.delete("/cosmos/accounts/failing-account")
        assert response.status_code == 404
        mock_instance.delete_account_async.assert_called_once_with("failing-account")
        app.dependency_overrides.clear()