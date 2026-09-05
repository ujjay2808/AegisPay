from functools import lru_cache
from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "aegispay-gateway"
    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://aegispay:aegispay@localhost:5432/aegispay"
    spend_cap_amount: Decimal = Decimal("5000.00")
    spend_cap_currency: str = "INR"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
