from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Конфигурация приложения.

    Attributes:
        env: Окружение (dev/prod)
        debug: Режим отладки
        api_prefix: Префикс для API эндпоинтов
        database_url: URL подключения к PostgreSQL
        redis_url: URL подключения к Redis
        jwt_secret: Секретный ключ для JWT токенов
        jwt_expires: Время жизни JWT токена в минутах
        update_delay: Задержка обновления данных в секундах
        free_tier_max_profit: Максимальный профит для бесплатного тарифа в %
    """

    env: Literal["dev", "prod"] = "dev"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # База данных
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/betscreener",
        description="PostgreSQL connection URL",
    )
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # JWT настройки
    jwt_secret: SecretStr = Field(default="secret", description="JWT secret key")
    jwt_expires: int = Field(default=15, description="JWT token expiration in minutes")
    jwt_refresh_expires_days: int = Field(
        default=20, description="JWT refresh token expiration in days"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")

    # Настройки сервиса
    update_delay: int = Field(default=10, ge=5, description="Update delay in seconds")
    free_tier_max_profit: float = Field(
        default=0.5, ge=0, le=100, description="Free tier max profit %"
    )

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"  # <-- ЭТО ПОЗВОЛИТ ИГНОРИРОВАТЬ ЛИШНИЕ ПЕРЕМЕННЫЕ В .env
    )

    @property
    def jwt_secret_value(self) -> str:
        return self.jwt_secret.get_secret_value()


settings = Settings()
