import os
from azure.core.exceptions import AzureError
from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, status, HTTPException, Depends
from app.services.logging_service import logger

from app.models.cosmos_models import (
CreateCosmosAccountRequest,
CosmosAccountStatusResponse,
ErrorResponse
)
from app.services.azure_cosmos_manager import AzureCosmosManager
from app.services.status_tracker import StatusTracker
from app.models.custom_types import CosmosAPIType, CosmosAccountStatus
from app.services.gmail_sender import GmailSender
from app.core.config.settings import get_settings, Settings

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
        #set Initial status
        # Set initial status
        StatusTracker.update_status(
            request.account_name,
            CosmosAccountStatus.QUEUED,
            "Provisioning request received"
        )

        # Start async provisioning
        background_tasks.add_task(
            execute_provisioning,
            manager,
            request.account_name,
            request.location,
            request.api_type
        )

        return StatusTracker.get_status(request.account_name)
    except ValueError as e:
        logger.error(str(e))
        StatusTracker.update_status(
            account_name=request.account_name,
            status=CosmosAccountStatus.ERROR,
            message=str(e),
        )
        #handle validation errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={
            "error_code": "VALIDATION_ERROR",
            "message": str(e),
        },)

    except AzureError as e:
        logger.error(str(e))
        StatusTracker.update_status(
            account_name=request.account_name,
            status=CosmosAccountStatus.ERROR,
            message=str(e),
        )
        #handle azure specific errors
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={
            "error_code": "AZURE_ERROR",
            "message": str(e),
        })

@router.get(
    "/accounts/{account_name}",
    response_model=CosmosAccountStatusResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Not found"},
    }
)
async def get_provisioning_status(
        account_name: str,
) -> CosmosAccountStatusResponse:
    """
    Get current provisioning status of CosmosDB account
    Args:
        account_name: CosmosDB account name

    Returns:
        Current provisioning status and details
    """
    account_status = StatusTracker.get_status(account_name)
    if account_status is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            "error_code": "ACCOUNT_NOT_FOUND",
            "message": f"Provisioning for CosmosDB account {account_name} not found",
        })
    return account_status


async def execute_provisioning(
        manager: AzureCosmosManager,
        account_name: str,
        location: str,
        api_type: CosmosAPIType,
)-> None:
    """Background task for actual provisioning"""
    try:
        #Update status to in-progress
        StatusTracker.update_status(
            account_name=account_name,
            status=CosmosAccountStatus.IN_PROGRESS,
            message="Resource provisioning started"
        )
        #perform actual provisioning
        await manager.create_account_async(
            account_name=account_name,
            location=location,
            api_type=api_type,
        )
        StatusTracker.update_status(
            account_name=account_name,
            status=CosmosAccountStatus.COMPLETED,
            message="Provisioning completed successfully"
        )
    except Exception as e:
        logger.error(str(e))
        #update status on error
        StatusTracker.update_status(
            account_name=account_name,
            status=CosmosAccountStatus.ERROR,
            message=str(e),
        )

async def handle_provisioning_failure(
        account_name: str,
        error: Exception,
        background_tasks: BackgroundTasks,
        settings: Settings = Depends(get_settings)
)->None:
    """Queue failure notification email on provisioning failure"""
    background_tasks.add_task(
        send_failure_notification,
        account_name,
        str(error),
        settings
    )

def send_failure_notification(
        account_name: str,
        error_message: str,
        settings: Settings
)->None:
    """Send email notification on provisioning failure"""
    try:
        with GmailSender(settings) as email_sender:
            email_sender.send(
                to=settings.GMAIL_ADDRESS,
                subject=f"Provisioning failed for {account_name}",
                body=f"""CosmosDB account provisioning faile:
                Account Name: {account_name}
                Error: {error_message}
                Required Action:
                1. Check Azure portal for resource status.
                2. Check detail.log file for errors
                3. Review account name availability
                4. Ensure location selected is avaialble for your account at this time.
                Provisioning failed for {account_name} with error: {error_message}"""
            )
    except Exception as e:
        logger.error(f"Email notification failed: {str(e)}")