import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

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
from azure.core.polling import AsyncLROPoller
from google.auth import message

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
            credential: TokenCredential,
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
        """Creates a standarized CosmosDB status response."""
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
            location: Azure region (e.g., 'eastus')
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
            return self._create_status_response(
                account_name,
                CosmosAccountStatus.ERROR,
               f"Azure Error: {str(err)}"
            )
    async def _send_notification(
            self,
            email: str,
            status: str
    )-> None:
        """Send email"""
        #TODO
        pass