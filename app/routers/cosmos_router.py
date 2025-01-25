from typing import Annotated
from datetime import datetime

from azure.core.exceptions import AzureError
from fastapi import APIRouter, BackgroundTasks, status, HTTPException, Depends, Response
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


# load_dotenv()
# subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
# resource_group = os.getenv("AZURE_RESOURCE_GROUP")

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
        # Set initial status
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
        # return {
        #     "status": CosmosAccountStatus.QUEUED,
        #     "account_name": request.account_name,
        #     "validation": "passed"
        # }
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
        #1. perform actual provisioning
        await manager.create_account_async(
            account_name=account_name,
            location=location,
            api_type=api_type,
        )
        #2. Update status
        StatusTracker.update_status(
            account_name=account_name,
            status=CosmosAccountStatus.COMPLETED,
            message="Provisioning completed successfully"
        )
        logger.info(StatusTracker.get_status(account_name))
        #.3 Send success notification
        send_success_notification(
            account_name=account_name,
            api_type=api_type,
            location=location,
            settings=settings
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



def send_failure_notification(
        account_name: str,
        error_message: str,
        settings: Settings
) -> None:
    """Send email notification on provisioning failure"""
    try:
        with GmailSender(settings) as email_sender:
            email_sender.send(
                to=settings.GMAIL_ADDRESS,
                subject=f"Provisioning failed for {account_name}",
                body=f"""CosmosDB account provisioning failed:
                Account Name: {account_name}
                Error: {error_message}
                Required Action:
                1. Check Azure portal for resource status.
                2. Check detail.log file for errors
                3. Review account name availability
                4. Ensure location selected is available for your account at this time.
                Provisioning failed for {account_name} with error: {error_message}"""
            )
    except Exception as e:
        logger.error(f"Email notification failed: {str(e)}")


def send_success_notification(
        account_name: str,
        api_type: CosmosAPIType,
        location: str,
        settings: Settings
) -> None:
    """
    Send success email notification with account details.

    Args:
        account_name: Provisioned account name
        api_type: Cosmos DB API type used
        location: Azure region where account was created
        settings: Application configuration with email details
    """
    try:
        with GmailSender(settings) as sender:
            sender.send(
                to=settings.GMAIL_ADDRESS,
                subject=f"✅ Cosmos DB Account Ready: {account_name}",
                body=f"""Your Azure Cosmos DB account has been successfully provisioned!

Account Details:
• Name: {account_name}
• API Type: {api_type.value}
• Location: {location}
• Provisioning Time: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}

Next Steps:
1. Create databases and containers
2. Configure access policies
3. Connect using connection strings

Azure Portal Link: https://portal.azure.com/#resource/subscriptions/{settings.AZURE_SUBSCRIPTION_ID}/resourceGroups/{settings.AZURE_RESOURCE_GROUP}/providers/Microsoft.DocumentDB/databaseAccounts/{account_name}
"""
            )
    except Exception as email_error:
        logger.error(f"Failed to send success notification: {str(email_error)}")


def send_deletion_success_email(
        account_name: str,
        settings: Settings
) -> None:
    """
    Send success email notification with account details.

    Args:
        account_name: Provisioned account name
        settings: Application configuration with email details
    """
    try:
        with GmailSender(settings) as sender:
            sender.send(
                to=settings.GMAIL_ADDRESS,
                subject=f"✅ Cosmos DB Account Deleted: {account_name}",
                body=f"""Your Azure Cosmos DB account {account_name} has been successfully deleted."""
            )
    except Exception as email_error:
        logger.error("EMail error: " + str(email_error))

def send_deletion_failure_email(
        account_name: str,
        error_message: str,
        settings: Settings
) -> None:
    """
    Send failure email notification with account details.

    Args:
        account_name: Provisioned account name
        error_message: Error message
        settings: Application configuration with email details
    """
    try:
        with GmailSender(settings) as sender:
            sender.send(
                to=settings.GMAIL_ADDRESS,
                subject=f"❌ Cosmos DB Account Deletion Failed: {account_name}",
                body=f"""Failed to delete Cosmos DB account {account_name}. Error: {error_message}"""
            )
    except Exception as email_error:
        logger.error("EMail error: " + str(email_error))


@router.delete(
    "/accounts/{account_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    # responses={
    #     status.HTTP_404_NOT_FOUND: {"description": "Not found"},
    #     status.HTTP_500_INTERNAL_SERVER_ERROR: { "description": "Internal Server Error"},
    # }
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
        await manager.delete_account_async(account_name)
        send_deletion_success_email(account_name, settings)
        # return Response(status_code=status.HTTP_204_NO_CONTENT)
   except ValueError as e:
       #account does not exist
        logger.error(str(e))
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


# async def execute_deletion(
#         manager: AzureCosmosManager,
#         account_name: str,
#         settings: Settings
# ) -> None:
#     """Background task for actual deletion"""
#     try:
#         #1. perform actual deletion
#         await manager.delete_account_async(account_name)
#         send_deletion_success_email(account_name, settings)
#     except Exception as e:
#         send_deletion_failure_email(account_name, str(e), settings)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail={
#                 "error_code": "AZURE_ERROR",
#                 "message": str(e),
#             }
#         ) from e