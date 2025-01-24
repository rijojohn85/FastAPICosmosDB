import os

from azure.core.exceptions import AzureError
from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, status, HTTPException, Depends

from app.models.cosmos_models import (
CreateCosmosAccountRequest,
CosmosAccountStatusResponse,
ErrorResponse
)
from app.services.azure_cosmos_manager import AzureCosmosManager
from app.models.custom_types import CosmosAPIType

router = APIRouter(
    prefix="/cosmos",
    tags=["cosmosdb"],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
    }
)

load_dotenv()
subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
resource_group = os.getenv("AZURE_RESOURCE_GROUP")

def get_cosmos_manager() -> AzureCosmosManager:
    """Dependency that provides a configured AzureCosmosManager instance"""
    return AzureCosmosManager(
        subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID"),
        resource_group=os.getenv("AZURE_RESOURCE_GROUP")
    )

@router.post(
    "/create",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CosmosAccountStatusResponse,
    responses={
        status.HTTP_202_ACCEPTED:{
            "descriptions": "Provisioning request accepted",
            "model": CosmosAccountStatusResponse
        },
        status.HTTP_400_BAD_REQUEST:{
            "descriptions": "Invalid request parameters",
            "model": ErrorResponse
        }
    }
)
async def create_cosmos_account(
        request: CreateCosmosAccountRequest,
        background_tasks: BackgroundTasks,
        manager: AzureCosmosManager = Depends(get_cosmos_manager)
)->CosmosAccountStatusResponse:
    """EndPoint to initiate CosmosDB account provisioning"""
    try:
        #initialte async provisioning
        response = await manager.create_account_async(
            account_name=request.account_name,
            location=request.location,
            api_type=request.api_type,
        )

        # add background task for post-provisioning operations
        background_tasks.add_task(
            send_provisioning_notification, #need to impl
            request.account_name,
            request.api_type,
        )
        return response
    except ValueError as e:
        #handle validation errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={
            "error_code": "VALIDATION_ERROR",
            "message": str(e),
        },)

    except AzureError as e:
        #handle azure specific errors
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={
            "error_code": "AZURE_ERROR",
            "message": str(e),
        })

async def send_provisioning_notification(account_name: str, api_type: str)->None:
    """Background  task for sending provisioning notification"""
    print("Sending provisioning notification")