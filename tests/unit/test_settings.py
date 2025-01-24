from app.core.config.settings import get_settings, Settings

def test_get_settings():
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.AZURE_SUBSCRIPTION_ID is not None

