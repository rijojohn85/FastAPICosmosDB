import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from azure.core.polling import AsyncLROPoller

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
    ) -> CosmosAccountStatusResponse:
        """Asynchronously provisions a new Azure Cosmos DB account.
        Args:
            account_name: Globally unique name of the Azure Cosmos DB account.(3-44 lowercase alphanumeric chars)
            location: Azure region (e.g., 'Central India')
            api_type: CosmosDB API type
        Returns:
            Status response with provisioning state
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
            poller = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.database_accounts.begin_create_or_update(
                    resource_group_name=self.resource_group,
                    account_name=account_name,
                    create_update_parameters=create_params,
                )
            )
            return self._create_status_response(
                account_name,
                CosmosAccountStatus.QUEUED,
                "Provisioning Initiated"
            )
        except AzureError as err:
            logger.error(err.message)
            return self._create_status_response(
                account_name,
                CosmosAccountStatus.ERROR,
               f"Azure Error: {str(err)}"
            )

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

    async def delete_account_async(self, account_name: str)->CosmosAccountStatusResponse:
        """Asynchronously deletes an Azure Cosmos DB account."""
        if not self.account_exists(account_name):
            raise ValueError(f"Account {account_name} does not exist.")
        try:
            #start async provisioning using thread pool executor
            poller = await asyncio.get_event_loop().run_in_executor(
                # None,
                # lambda: self.client.database_accounts.begin_delete(
                #     resource_group_name=self.resource_group,
                #     account_name=account_name,
                # ),
                None,
                lambda: self.client.database_accounts.begin_delete(
                    resource_group_name=self.resource_group,
                    account_name=account_name,
                ),
            )
            return self._create_status_response(
                account_name,
                CosmosAccountStatus.QUEUED,
                "Provisioning Initiated"
            )
        except AzureError as err:
            logger.error(err.message)
            return self._create_status_response(
                account_name,
                CosmosAccountStatus.ERROR,
                f"Azure Error: {str(err)}"
            )
