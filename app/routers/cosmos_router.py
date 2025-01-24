from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, status
from app.models.cosmos_models import (
CreateCosmosAccountRequest,
CosmosAccountStatusResponse,
ErrorResponse
)
from app.models.custom_types import CosmosAccountStatus

router = APIRouter(
    prefix="/cosmos",
    tags=["cosmosdb"],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
    }
)

@router.post(
    "/accounts",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CosmosAccountStatusResponse,
    responses={
        status.HTTP_202_ACCEPTED:{
            "descriptions": "Provisioning request accepted",
            "model": CosmosAccountStatusResponse
        },
    }
)
async def create_cosmos_account(request: CreateCosmosAccountRequest, background_tasks: BackgroundTasks)->CosmosAccountStatusResponse:
    # Temporary implementation to satisfy type checker
    return CosmosAccountStatusResponse(
        account_name=request.account_name,
        status=CosmosAccountStatus.QUEUED,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        message="Provisioning queued - implementation pending"
    )
    pass
