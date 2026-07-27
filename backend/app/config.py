from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Muhit sozlamalari — .env faylidan o'qiladi."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/qoraqalpogiston"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 12 * 60

    # Claude API. Kalit bo'lmasa AI endpointlari deterministik "offline"
    # rejimga tushadi — platforma baribir ishlaydi.
    anthropic_api_key: str | None = None
    claude_model: str = "claude-opus-5"

    cors_origins: str = "http://localhost:3000,http://localhost:3100"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
