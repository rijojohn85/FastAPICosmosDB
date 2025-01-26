import re
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from app.models.custom_types import CosmosAPIType, CosmosAccountStatus

class CreateCosmosAccountRequest(BaseModel):
    account_name: str = Field(
        ...,
        min_length=3,
        max_length=44,
        pattern=r"^[a-z]+[a-z0-9-]{1,42}[a-z0-9]$",
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
    # @field_validator("account_name")
    # def validate_account_name(cls, value: str)->str:
    #     if not re.fullmatch(
    #         r"^[a-z]+[a-z0-9-]{1,42}[a-z0-9]$",
    #         value
    #     ):
    #         raise ValueError("""
    #         Invalid Account name. Must be:\n
    #         - between 3 and 44 characters\n
    #         - lowercase letters, numbers, and hyphens only\n
    #         - cannot start or end with a hyphen\n
    #         - cannot have consecutive hyphens.
    #         """)
    #     return value

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

