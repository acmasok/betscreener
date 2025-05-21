from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Application configuration.

    Attributes:
        env: Environment (dev/prod)
        debug: Debug mode
        api_prefix: API endpoints prefix
        database_url: PostgreSQL connection URL
        redis_url: Redis connection URL
        jwt_secret: JWT tokens secret key
        jwt_expires: JWT token lifetime in minutes
        update_delay: Data update delay in seconds
        free_tier_max_profit: Maximum profit for free tier in %
    """

    env: Literal["dev", "prod"] = "dev"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Security Settings
    rate_limit_window: int = Field(
        default=300, description="Time window for counting attempts (seconds)"
    )
    rate_limit_max_requests: int = Field(
        default=30, description="Maximum attempts within the window"
    )
    ban_threshold: int = Field(default=20, description="Number of attempts before ban")
    initial_ban_time: int = Field(default=900, description="Initial ban duration (seconds)")
    max_ban_time: int = Field(default=3600, description="Maximum ban duration (seconds)")
    ban_multiplier: float = Field(default=2.0, description="Multiplier for increasing ban time")
    captcha_required: bool = Field(default=True, description="Require CAPTCHA verification")
    captcha_site_key: Optional[str] = Field(default=None, description="reCAPTCHA site key")
    captcha_secret_key: Optional[str] = Field(default=None, description="reCAPTCHA secret key")

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/betscreener",
        description="PostgreSQL connection URL",
    )
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # JWT settings
    jwt_secret: SecretStr = Field(default="secret", description="JWT secret key")
    jwt_expires: int = Field(default=15, description="JWT token expiration in minutes")
    jwt_refresh_expires_days: int = Field(
        default=20, description="JWT refresh token expiration in days"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")

    # Service settings
    update_delay: int = Field(default=10, ge=5, description="Update delay in seconds")
    free_tier_max_profit: float = Field(
        default=0.5, ge=0, le=100, description="Free tier max profit %"
    )

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )

    @property
    def jwt_secret_value(self) -> str:
        return self.jwt_secret.get_secret_value()


settings = Settings()
