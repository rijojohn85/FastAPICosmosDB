from enum import Enum
from typing import Literal, TypedDict

class CosmosAPIType(str, Enum):
    SQL = "sql"
    MONGO = "mongo"

class CosmosAccountStatus(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR="error"

class EmailNotification(TypedDict):
    recipient: str
    subject: str
    message: str

class ProvisioningContext(TypedDict):
    account_name: str
    location: str
    api_type: CosmosAPIType
    initiated_by: str