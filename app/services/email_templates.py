from app.models.custom_types import CosmosAPIType
from app.core.config.settings import Settings
from datetime import datetime
from app.services.email_service import send_email
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
    subject =  f"✅ Cosmos DB Account Ready: {account_name}"
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
    send_email(subject, body, settings)


def send_deletion_failure_email(
        account_name: str,
        error_message: str,
        settings: Settings
) -> None:
    """
    Send deletion failure email notification with account details.

    Args:
        account_name: Provisioned account name
        error_message: Error message
        settings: Application configuration with email details
    """
    subject=f"❌ Cosmos DB Account Deletion Failed: {account_name}"
    body=f"""Failed to delete Cosmos DB account {account_name}. Error: {error_message}"""
    send_email( subject, body, settings)

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
    subject=f"✅ Cosmos DB Account Deleted: {account_name}"
    body=f"Your Azure Cosmos DB account {account_name} has been successfully deleted."
    send_email(subject, body, settings)

def send_failure_notification(
        account_name: str,
        error_message: str,
        settings: Settings
) -> None:
    """Send email notification on provisioning failure"""
    subject:str = f"Provisioning failed for {account_name}"
    body: str= f"""CosmosDB account provisioning failed:
                Account Name: {account_name}
                Error: {error_message}
                Required Action:
                1. Check Azure portal for resource status.
                2. Check detail.log file for errors
                3. Review account name availability
                4. Ensure location selected is available for your account at this time.
                Provisioning failed for {account_name} with error: {error_message}"""
    send_email(subject, body, settings)
