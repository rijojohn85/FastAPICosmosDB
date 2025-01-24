from datetime import datetime
from typing import Optional, Dict
from app.models.custom_types import CosmosAccountStatus
from app.models.cosmos_models import CosmosAccountStatusResponse

class StatusTracker:
    """
    Tracks Provisioning status for a Cosmos Account.
    Attributes:
        _statues(Dict[str, CosmosAccountStatusResponse]):
            Dictionary of Cosmos Account Status Responses.
    """
    _statues: Dict[str, CosmosAccountStatusResponse] = {}

    @classmethod
    def update_status(
            cls,
            account_name: str,
            status: CosmosAccountStatus,
            message: Optional[str] = None
    )->None:
        """
        Updates the status of a Cosmos Account provisioning.
        Args:
            account_name: Unique name of the Cosmos Account.
            status: Current status of the CosmosAccountStatus enum
            message: Optional message to display
        """
        now = datetime.now()
        cls._statues[account_name] = CosmosAccountStatusResponse(
            account_name=account_name,
            status=status,
            created_at=now,
            updated_at=now,
            message=message
        )
    @classmethod
    def get_status(
            cls,
            account_name: str,
    )->Optional[CosmosAccountStatusResponse]:
        """
        Returns the status of a Cosmos Account provisioning.
        Args:
            account_name: Unique name of the Cosmos Account.
        Returns:
            CosmosAccountStatusResponse if found, None otherwise.
        """
        return cls._statues.get(account_name, None)