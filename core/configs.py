from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LANDING_AI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_MISTRAL_ENDPOINT: str
    OPENAI_API_KEY: str
    AZURE_MISTRAL_API_KEY: str
    OPENAI_API_VERSION: str
    TESSERACT_CMD: str

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )


@lru_cache()
def get_settings() -> Settings:
    try:
        return Settings()
    except Exception as e:
        raise RuntimeError("Failed to load settings") from e
