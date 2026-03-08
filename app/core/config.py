import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_DEFAULT_SECRET = "change-me-in-production"
_DEFAULT_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/task_manager"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = _DEFAULT_DB_URL
    secret_key: str = _DEFAULT_SECRET
    environment: str = "development"

    # CORS: comma-separated list of allowed origins
    allowed_origins: str = "http://localhost:8000"

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        if self.environment == "production":
            if self.secret_key == _DEFAULT_SECRET:
                raise ValueError(
                    "SECRET_KEY must be set via environment variable before running in production."
                )
            if self.database_url == _DEFAULT_DB_URL:
                raise ValueError(
                    "DATABASE_URL must be set via environment variable before running in production."
                )
        else:
            if self.secret_key == _DEFAULT_SECRET:
                logger.warning(
                    "WARNING: Using the default SECRET_KEY. "
                    "Set SECRET_KEY env var before deploying to production."
                )
        return self


settings = Settings()
