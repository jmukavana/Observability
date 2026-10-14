from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://observability:observability@localhost:4432/observability"
    )
    oidc_issuer: str = "http://localhost:4080/realms/observability"
    oidc_audience: str = "observability-api"

    @property
    def oidc_jwks_url(self) -> str:
        return f"{self.oidc_issuer}/protocol/openid-connect/certs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
