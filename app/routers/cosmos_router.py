from typing import Annotated
from app.services.email_templates import  send_failure_notification, send_deletion_failure_email
from azure.core.exceptions import AzureError
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
from app.core.config.settings import get_settings, Settings
router = APIRouter(
    prefix="/cosmos",
    tags=["cosmosdb"],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
    }
)



async def get_cosmos_manager(settings: Annotated[Settings, Depends(get_settings)]) -> AzureCosmosManager:
    """Dependency that provides a configured AzureCosmosManager instance"""
    return AzureCosmosManager(
        subscription_id=settings.AZURE_SUBSCRIPTION_ID,
        resource_group=settings.AZURE_RESOURCE_GROUP
    )


@router.post(
    "/accounts",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CosmosAccountStatusResponse,
    responses={
        status.HTTP_202_ACCEPTED: {
            "descriptions": "Provisioning request accepted",
            "model": CosmosAccountStatusResponse
        },
        status.HTTP_400_BAD_REQUEST: {
            "descriptions": "Invalid Account name",
            "content": {"application/json": {"example": {"detail":"Invalid account name. Must be: ..."}}}
        }
    }
)
async def create_cosmos_account(
        request: CreateCosmosAccountRequest,
        background_tasks: BackgroundTasks,
        manager: Annotated[AzureCosmosManager, Depends(get_cosmos_manager)],
        settings: Annotated[Settings, Depends(get_settings)]
) -> CosmosAccountStatusResponse:
    """EndPoint to initiate CosmosDB account provisioning"""
    try:
        # set Initial status
        StatusTracker.update_status(
            account_name=request.account_name,
            status=CosmosAccountStatus.QUEUED,
        )

        # Start async provisioning
        background_tasks.add_task(
            execute_provisioning,
            manager,
            request.account_name,
            request.location,
            request.api_type,
            settings
        )

        return StatusTracker.get_status(request.account_name)
    except ValueError as e:
        logger.error(str(e))
        StatusTracker.update_status(
            account_name=request.account_name,
            status=CosmosAccountStatus.ERROR,
            message=str(e),
        )
        # handle validation errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={
            "error_code": "VALIDATION_ERROR",
            "message": str(e),
        }, )

    except AzureError as e:
        background_tasks.add_task(
            send_failure_notification,
            request.account_name,
            str(e),
            settings
        )
        logger.error(str(e))
        StatusTracker.update_status(
            account_name=request.account_name,
            status=CosmosAccountStatus.ERROR,
            message=str(e),
        )
        # handle azure specific errors
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={
            "error_code": "AZURE_ERROR",
            "message": str(e),
        })
    except Exception as e:
        background_tasks.add_task(
            send_failure_notification,
            request.account_name,
            str(e),
            settings
        )
        logger.error(str(e))
        StatusTracker.update_status(
            account_name=request.account_name,
            status=CosmosAccountStatus.ERROR,
            message=str(e),
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={
            "error_code": "INTERNAL_ERROR"+" "+str(e),
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
        settings: Settings,
) -> None:
    """Background task for actual provisioning"""
    try:
        # Update status to in-progress
        StatusTracker.update_status(
            account_name=account_name,
            status=CosmosAccountStatus.IN_PROGRESS,
            message="Resource provisioning started"
        )
        # perform actual provisioning
        await manager.create_account_async(
            account_name=account_name,
            location=location,
            api_type=api_type,
        )
    except Exception as e:
        logger.error(str(e))
        # update status on error
        StatusTracker.update_status(
            account_name=account_name,
            status=CosmosAccountStatus.ERROR,
            message=str(e),
        )
        send_failure_notification(
            account_name,
            str(e),
            settings
        )
@router.delete(
    "/accounts/{account_name}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_cosmos_account(
        account_name: str,
        background_tasks: BackgroundTasks,
        manager: Annotated[AzureCosmosManager, Depends(get_cosmos_manager)],
        settings: Annotated[Settings, Depends(get_settings)]) -> None:
   """
   Deletes a Cosmos DB account and sends appropriate notifications

   Args:
        account_name: Name of the account to delete
        background_tasks: BackgroundTasks dependency
        manager: Injected AzureCosmosManager dependency
        settings: Injected Settings dependency
    Raises:
        HTTPException: If account does not exist or errors
   """
   try:
        StatusTracker.update_status(
          account_name=account_name,
          status=CosmosAccountStatus.QUEUED,
            message="Deletion Initiated"
        )
        await manager.delete_account_async(account_name)
        StatusTracker.update_status(
            account_name,
            CosmosAccountStatus.IN_PROGRESS,
            message="Deletion request sent to Azure"
        )
   except ValueError as e:
       #account does not exist
        StatusTracker.update_status(
            account_name=account_name,
            status=CosmosAccountStatus.ERROR,
            message="Account not found"
        )
        send_deletion_failure_email(
                account_name,
                str(e),
           settings
        )
        raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail={
                "error_code": "ACCOUNT_NOT_FOUND",
                "message": str(e),
              }
        )
   except AzureError as e:
         #Azure error
         send_deletion_failure_email(
             account_name,
             str(e),
             settings
         )
         raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail={
                "error_code": "AZURE_ERROR",
                "message": str(e),
              }
         )