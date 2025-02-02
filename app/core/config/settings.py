from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Application configuration setting with env vars
    Inherits from Pydantic BaseSettings for auto env vars
    loading
    """
    AZURE_SUBSCRIPTION_ID: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="Azure subscription id(UUID format)",
    )
    AZURE_RESOURCE_GROUP: str = Field(
        ...,
        min_length=1,
        max_length=90,
        description="Azure resource group name",
    )

    GMAIL_ADDRESS: str= Field(
        ...,
        description="Email address for sending email",
    )
    GMAIL_PASSWORD: str = Field(
        ...,
        description="Email password for sending email",
    )
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    # class Config:
    #     env_file = ".env"
    #     env_file_encoding = "utf-8"
def get_settings() -> Settings:
    """
    Dependency function to retrieve
    configuration settings.
    Returns:
        Settings: configuration settings instance.
    """
    return Settings()