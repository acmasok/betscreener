from dataclasses import dataclass
from datetime import datetime
import redis
from typing import Optional


@dataclass
class SecurityConfig:
    # Базовые настройки для rate limit
    rate_limit_window: int = 300  # 5 минут
    rate_limit_max_requests: int = 30  # 30 попыток за 5 минут (увеличено, так как есть CAPTCHA)

    # Настройки бана
    ban_threshold: int = 100  # Увеличенный порог бана (так как есть CAPTCHA)
    initial_ban_time: int = 900  # 15 минут
    max_ban_time: int = 3600  # 1 час


class LoginAttemptResult:
    def __init__(self,
                 success: bool,
                 is_banned: bool = False,
                 ban_time: int = 0,
                 message: str = ""):
        self.success = success
        self.is_banned = is_banned
        self.ban_time = ban_time
        self.message = message


class SecuritySystem:
    def __init__(self, redis_client: redis.Redis, config: SecurityConfig = SecurityConfig()):
        self.redis = redis_client
        self.config = config

    def handle_login_attempt(self,
                             identifier: str,
                             captcha_response: Optional[str]) -> LoginAttemptResult:
        """
        Обрабатывает попытку входа
        """
        # Проверяем наличие CAPTCHA
        if not captcha_response:
            return LoginAttemptResult(
                success=False,
                message="Необходимо пройти проверку CAPTCHA"
            )

        # Проверяем бан
        ban_key = f"ban:{identifier}"
        ban_time = self.redis.ttl(ban_key)

        if ban_time > 0:
            return LoginAttemptResult(
                success=False,
                is_banned=True,
                ban_time=ban_time,
                message=f"Доступ временно заблокирован на {ban_time} секунд"
            )

        # Проверяем rate limit
        rate_key = f"rate:{identifier}"
        attempts = self.redis.incr(rate_key)

        if attempts == 1:
            self.redis.expire(rate_key, self.config.rate_limit_window)

        if attempts > self.config.rate_limit_max_requests:
            ban_time = min(
                self.config.initial_ban_time * (attempts // self.config.rate_limit_max_requests),
                self.config.max_ban_time
            )
            self.redis.setex(ban_key, ban_time, 1)

            return LoginAttemptResult(
                success=False,
                is_banned=True,
                ban_time=ban_time,
                message=f"Превышен лимит попыток. Доступ заблокирован на {ban_time} секунд"
            )

        return LoginAttemptResult(
            success=True,
            message="Проверки пройдены"
        )

    def reset_attempts(self, identifier: str):
        """Сбрасывает счетчики попыток при успешном входе"""
        keys = [f"rate:{identifier}", f"ban:{identifier}"]
        self.redis.delete(*keys)