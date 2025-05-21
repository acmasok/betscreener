"""
Security system for authentication rate limiting and protection
Created: 2025-05-21
Author: acmasok
"""

import logging
from typing import Optional

import aiohttp
import redis.asyncio as redis
from fastapi import Depends
from pydantic import BaseModel

from ..core.config import settings
from .deps import get_redis_client


class LoginAttemptResult(BaseModel):
    """Result of security check attempt"""

    success: bool
    is_banned: bool = False
    ban_time: int = 0
    message: str = ""
    remaining_attempts: Optional[int] = None


class SecuritySystem:
    """Main security system implementation"""

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize security system

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)

    async def _get_ban_history(self, identifier: str) -> int:
        """Get number of previous bans for identifier"""
        ban_history_key = f"ban_history:{identifier}"
        ban_count = await self.redis.get(ban_history_key)
        return int(ban_count) if ban_count else 0

    async def _increment_ban_history(self, identifier: str):
        """Increment ban counter and set expiration"""
        ban_history_key = f"ban_history:{identifier}"
        await self.redis.incr(ban_history_key)
        # Store ban history for 30 days
        await self.redis.expire(ban_history_key, 60 * 60 * 24 * 30)

    async def _calculate_ban_time(self, identifier: str, current_attempts: int) -> int:
        """
        Calculate ban duration based on history and current attempts

        Args:
            identifier: User identifier (IP or email)
            current_attempts: Number of current attempts

        Returns:
            Ban duration in seconds
        """
        ban_count = await self._get_ban_history(identifier)

        # Base ban time
        ban_time = settings.initial_ban_time

        # Increase based on ban history
        if ban_count > 0:
            ban_time *= settings.ban_multiplier**ban_count

        # Additional increase for excessive attempts
        attempts_multiplier = current_attempts / settings.ban_threshold
        if attempts_multiplier > 1:
            ban_time *= attempts_multiplier

        return min(int(ban_time), settings.max_ban_time)

    async def verify_captcha(self, captcha_response: str) -> bool:
        """
        Verify CAPTCHA response with Google reCAPTCHA

        Args:
            captcha_response: CAPTCHA response token

        Returns:
            bool: True if verification successful
        """
        if not settings.captcha_secret_key:
            self.logger.error("CAPTCHA secret key not configured")
            return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://www.google.com/recaptcha/api/siteverify",
                    data={"secret": settings.captcha_secret_key, "response": captcha_response},
                ) as response:
                    result = await response.json()
                    return result.get("success", False)
        except Exception as e:
            self.logger.error(f"CAPTCHA verification error: {str(e)}")
            return False

    async def handle_login_attempt(
        self, identifier: str, captcha_response: Optional[str]
    ) -> LoginAttemptResult:
        """
        Handle login/register attempt with security checks

        Args:
            identifier: User identifier (IP or email)
            captcha_response: CAPTCHA response token

        Returns:
            LoginAttemptResult with attempt status
        """
        try:
            # Check CAPTCHA if required
            if settings.captcha_required:
                if not captcha_response:
                    return LoginAttemptResult(
                        success=False,
                        message="CAPTCHA verification required. Please complete the verification.",
                    )
                if not await self.verify_captcha(captcha_response):
                    return LoginAttemptResult(
                        success=False, message="CAPTCHA verification failed. Please try again."
                    )

            # Check current ban
            ban_key = f"ban:{identifier}"
            ban_time = await self.redis.ttl(ban_key)

            if ban_time > 0:
                return LoginAttemptResult(
                    success=False,
                    is_banned=True,
                    ban_time=ban_time,
                    message=f"Access temporarily blocked. Please try again in {ban_time} seconds.",
                )

            # Check rate limit
            rate_key = f"rate:{identifier}"
            attempts = await self.redis.incr(rate_key)

            # Set TTL on first attempt
            if attempts == 1:
                await self.redis.expire(rate_key, settings.rate_limit_window)

            # Check if limit exceeded
            if attempts > settings.rate_limit_max_requests:
                ban_time = await self._calculate_ban_time(identifier, attempts)
                await self.redis.setex(ban_key, ban_time, 1)
                await self._increment_ban_history(identifier)

                self.logger.warning(
                    f"Security violation: Ban applied to {identifier} "
                    f"Duration: {ban_time}s, Attempts: {attempts}, "
                    f"Previous bans: {await self._get_ban_history(identifier)}"
                )

                return LoginAttemptResult(
                    success=False,
                    is_banned=True,
                    ban_time=ban_time,
                    message=f"Too many attempts. Access blocked for {ban_time} seconds.",
                )

            remaining_attempts = settings.rate_limit_max_requests - attempts

            return LoginAttemptResult(
                success=True,
                message="Security checks passed",
                remaining_attempts=remaining_attempts,
            )

        except Exception as e:
            self.logger.error(f"Security check error for {identifier}: {str(e)}")
            return LoginAttemptResult(success=False, message="Security check error occurred")

    async def reset_attempts(self, identifier: str):
        """
        Reset attempt counters after successful authentication

        Args:
            identifier: User identifier to reset
        """
        try:
            keys = [f"rate:{identifier}", f"ban:{identifier}"]
            await self.redis.delete(*keys)
            self.logger.info(f"Reset security attempts for {identifier}")

        except Exception as e:
            self.logger.error(f"Error resetting attempts for {identifier}: {str(e)}")

    async def get_security_status(self, identifier: str) -> dict:
        """
        Get current security status for identifier

        Args:
            identifier: User identifier to check

        Returns:
            Dict with current security status
        """
        try:
            rate_key = f"rate:{identifier}"
            ban_key = f"ban:{identifier}"
            ban_history_key = f"ban_history:{identifier}"

            attempts = await self.redis.get(rate_key)
            ban_time = await self.redis.ttl(ban_key)
            ban_count = await self.redis.get(ban_history_key)

            return {
                "current_attempts": int(attempts) if attempts else 0,
                "is_banned": ban_time > 0,
                "ban_time_remaining": max(0, ban_time),
                "total_bans": int(ban_count) if ban_count else 0,
                "remaining_attempts": max(
                    0, settings.rate_limit_max_requests - (int(attempts) if attempts else 0)
                ),
            }

        except Exception as e:
            self.logger.error(f"Error getting security status for {identifier}: {str(e)}")
            return {"error": "Failed to get security status", "message": str(e)}


class SecuritySystemDependency:
    """Singleton dependency for SecuritySystem"""

    _instance = None

    def __init__(self, redis_client: redis.Redis):
        self.security_system = SecuritySystem(redis_client)

    @classmethod
    async def get_instance(
        cls, redis_client: redis.Redis = Depends(get_redis_client)
    ) -> SecuritySystem:
        if cls._instance is None:
            cls._instance = cls(redis_client)
        return cls._instance.security_system


# FastAPI dependency
get_security_system = SecuritySystemDependency.get_instance
