from functools import lru_cache
from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_blocked_merchant_ids(raw: str | None = None) -> frozenset[str]:
    if raw is None:
        return frozenset()
    return frozenset(
        value.strip().casefold()
        for value in raw.split(",")
        if value.strip() and value.strip().casefold()
    )


class Settings(BaseSettings):
    service_name: str = "aegispay-gateway"
    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://aegispay:aegispay@localhost:5432/aegispay"
    spend_cap_amount: Decimal = Decimal("5000.00")
    spend_cap_currency: str = "INR"
    blocked_merchant_ids: str = ""
    audit_enabled: bool = False
    audit_service_url: str = "http://localhost:8080"
    audit_timeout_seconds: float = 30.0
    audit_api_key: str = ""

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
