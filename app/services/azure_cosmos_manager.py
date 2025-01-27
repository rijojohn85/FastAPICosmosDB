import asyncio
from typing import Optional, Dict, Any, Annotated
from datetime import datetime
from azure.core.polling import AsyncLROPoller

import app.services.email_templates
from app.core.config.settings import get_settings
from app.services.logging_service import logger

from azure.identity import AzureCliCredential
from azure.core.credentials import TokenCredential
from azure.mgmt.cosmosdb import CosmosDBManagementClient
from azure.mgmt.cosmosdb.models import (
    DatabaseAccountCreateUpdateParameters,
Location,
DatabaseAccountKind,
DatabaseAccountGetResults,
ApiProperties
)

from azure.core.exceptions import AzureError

from app.models.custom_types import CosmosAPIType, CosmosAccountStatus
from app.models.cosmos_models import CosmosAccountStatusResponse
from app.services.status_tracker import StatusTracker


class AzureCosmosManager:
    """Manages Azure Cosmos DB account lifecycle operations with async support.
    Attributes:
        subscription_id: Azure subscription identifier
        resource_group: Azure resource group name
        credential: Azure authentication credential
        client: Cosmos DB Management client
    """
    def __init__(
            self,
            subscription_id: str,
            resource_group: str,
            credential: TokenCredential=None,
    ):
        """Initializes AzureCosmosManager
        Args:
            subscription_id: Azure subscription identifier
            resource_group: Azure resource group name
            credential: Azure authentication credential(default: AzureCliCredential)
        """
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.credential = credential or AzureCliCredential()
        self.client = CosmosDBManagementClient(
            self.credential,
            self.subscription_id,
        )
    def _map_api_type(self, api_type: CosmosAPIType) -> DatabaseAccountKind:
        """Maps our API type enum to Azure SDK Enum."""
        return {
            CosmosAPIType.SQL: DatabaseAccountKind.GLOBAL_DOCUMENT_DB,
            CosmosAPIType.MONGO: DatabaseAccountKind.MONGO_DB,
        }[api_type]
    def _get_api_properties(self, api_type: CosmosAPIType) -> Optional[ApiProperties]:
        """Returns API-specific properties for account creation."""
        if api_type == CosmosAPIType.MONGO:
            return ApiProperties(server_version="3.2")
        return None
    def _create_status_response(
            self,
            account_name:str,
            status: CosmosAccountStatus,
            resp_message: Optional[str]=None) -> CosmosAccountStatusResponse:
        """Creates a standardized CosmosDB status response."""
        now = datetime.now()
        return CosmosAccountStatusResponse(
            account_name=account_name,
            status=status,
            created_at=now,
            updated_at=now,
            message=resp_message,
        )
    async def create_account_async(
            self,
            account_name: str,
            location: str,
            api_type: CosmosAPIType,
    )->None:
        """Asynchronously provisions a new Azure Cosmos DB account.
        Args:
            account_name: Globally unique name of the Azure Cosmos DB account.(3-44 lowercase alphanumeric chars)
            location: Azure region (e.g., 'Central India')
            api_type: CosmosDB API type
        Raises:
            AzureError: If Azure SDK operation fails
        """
        try:
            #map API type to Azure SDK Enum
            kind = self._map_api_type(api_type)

            #Prepare account creation Parameters
            create_params = DatabaseAccountCreateUpdateParameters(
                location=location,
                kind=kind,
                locations=[Location(
                    location_name=location,
                    failover_priority=0
                )],
                database_account_offer_type="Standard",
                api_properties=self._get_api_properties(api_type),
            )
            #start async provisioning using thread pool executor
            def sync_create_and_wait():
                poller = self.client.database_accounts.begin_create_or_update(
                    resource_group_name=self.resource_group,
                    account_name=account_name,
                    create_update_parameters=create_params
                )
                return poller.result()
            future = asyncio.get_event_loop().run_in_executor(None, sync_create_and_wait)
            def callback(fut: asyncio.Future[None])->None:
                try:
                    fut.result()
                    StatusTracker.update_status(
                        account_name=account_name,
                        status=CosmosAccountStatus.COMPLETED,
                        message="Provisioning completed successfully"
                    )
                    app.services.email_templates.send_success_notification(
                        account_name,
                        api_type,
                        location,
                        get_settings()
                    )
                except Exception as e:
                    logger.error(str(e))
                    StatusTracker.update_status(
                        account_name=account_name,
                        status=CosmosAccountStatus.ERROR,
                        message=str(e),
                    )
                    app.services.email_templates.send_failure_notification(
                        account_name,
                        str(e),
                        get_settings()
                    )
            future.add_done_callback(callback)

        except AzureError as err:
            logger.error(err.message)
            raise Exception(">>> Error: " + str(err) + " <<<")

    def get_account_async(self, account_name: str)->Optional[DatabaseAccountGetResults]:
        """Asynchronously retrieves an Azure Cosmos DB account."""
        try:
            return self.client.database_accounts.get(
                self.resource_group,
                account_name
            )
        except AzureError as e:
            logger.error(e)
            return None

    def account_exists(self, account_name:str)->bool:
        """Checks if an account exists."""
        account = self.get_account_async(account_name)
        return account is not None

    async def delete_account_async(self, account_name: str)->None:
        """Asynchronously deletes an Azure Cosmos DB account."""
        if not self.account_exists(account_name):
            raise ValueError(f"Account {account_name} does not exist.")
        try:
            #start async provisioning using thread pool executor
            #start async provisioning using thread pool executor
            def sync_create_and_wait():
                poller = self.client.database_accounts.begin_delete(
                    resource_group_name=self.resource_group,
                    account_name=account_name,
                )
                return poller.result()
            future = asyncio.get_event_loop().run_in_executor(None, sync_create_and_wait)
            def callback(fut: asyncio.Future[None])->None:
                try:
                    fut.result()
                    StatusTracker.update_status(
                        account_name=account_name,
                        status=CosmosAccountStatus.COMPLETED,
                        message="Deleting completed successfully"
                    )
                    app.services.email_templates.send_deletion_success_email(
                        account_name,
                        get_settings()
                    )
                except Exception as e:
                    logger.error(str(e))
                    StatusTracker.update_status(
                        account_name=account_name,
                        status=CosmosAccountStatus.ERROR,
                        message=str(e),
                    )
                    app.services.email_templates.send_deletion_failure_email(
                        account_name,
                        str(e),
                        get_settings()
                    )
            future.add_done_callback(callback)
            # poller = await asyncio.get_event_loop().run_in_executor(
            #     None,
            #     lambda: self.client.database_accounts.begin_delete(
            #         resource_group_name=self.resource_group,
            #         account_name=account_name,
            #     ),
            # )
            # def callback(fut: asyncio.Future[None])->None:
            #     if fut.exception():
            #         logger.error(fut.exception())
            #         StatusTracker.update_status(
            #             account_name=account_name,
            #             status=CosmosAccountStatus.ERROR,
            #             message=str(fut.exception())
            #         )
            #         app.services.email_templates.send_deletion_failure_email(account_name, str(fut.exception()), get_settings())
            #     else:
            #         StatusTracker.update_status(
            #             account_name=account_name,
            #             status=CosmosAccountStatus.COMPLETED,
            #             message="Delete completed successfully"
            #         )
            #         app.services.email_templates.send_deletion_success_email(
            #             account_name,
            #             get_settings()
            #         )
            # poller.add_done_callback(callback)
        except AzureError as err:
            logger.error(err.message)
            raise Exception(">>> Error: " + str(err) + " <<<")
