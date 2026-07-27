from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Muhit sozlamalari — .env faylidan yoki muhit o'zgaruvchilaridan o'qiladi."""

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

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, v: str) -> str:
        """
        Hosting provayderlari (Neon, Render, Heroku) ulanish satrini
        `postgres://` yoki `postgresql://` ko'rinishida beradi. SQLAlchemy
        bunda psycopg2 ni qidiradi — u o'rnatilmagan, natijada ilova
        ishga tushmaydi. Shuning uchun drayver ochiq ko'rsatiladi.
        """
        for prefix in ("postgresql+psycopg://", "postgresql+psycopg2://"):
            if v.startswith(prefix):
                return v
        for prefix in ("postgresql://", "postgres://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix) :]
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
