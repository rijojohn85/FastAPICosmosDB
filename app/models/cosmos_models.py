from datetime import datetime
from pydantic import BaseModel, Field
from app.models.custom_types import CosmosAPIType, CosmosAccountStatus

class CreateCosmosAccountRequest(BaseModel):
    account_name: str = Field(
        ...,
        min_length=3,
        max_length=44,
        pattern=r'[a-z0-9-]+$',
        examples=["my-cosmos-account"],
    )
    location: str=Field(
        ...,
        min_length=5,
        examples=["Central India"]
    )
    api_type: CosmosAPIType=Field(
        default=CosmosAPIType.SQL,
        examples=["sql"]
    )

class CosmosAccountStatusResponse(BaseModel):
    account_name: str
    status: CosmosAccountStatus
    created_at: datetime
    updated_at: datetime
    message: str | None=None

class ErrorResponse(BaseModel):
    detail: str
    error_code: str
    timestamp: datetime

