from passlib.context import CryptContext
from forkscan.core.config import settings
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_ban_time(
        fails: int,
        max_attempts: int = settings.max_failed_attempts,
        min_attempts: int = settings.min_attempts_for_ban,
        initial_ban: int = settings.initial_ban_time,
        max_ban: int = settings.max_ban_time,
        multiplier: int = settings.ban_multiplier,
) -> int:
    """
    Возвращает время бана с более плавным нарастанием.

    Пример для multiplier=2:
    - 3 ошибки: 1 минута
    - 4 ошибки: 2 минуты
    - 5 ошибок: 4 минуты
    - ...
    - 10 ошибок: 128 минут (~2 часа)
    - >10 ошибок: 24 часа
    """
    if fails < min_attempts:
        return 0

    if fails >= max_attempts:
        return max_ban

    return min(initial_ban * (multiplier ** (fails - min_attempts)), max_ban)

def get_ban_time_interval(attempts: int, min_attempts: int) -> int:
    if attempts <= min_attempts:
        return 0
    steps = [600, 1800, 7200, 43200, 86400]
    idx = min(attempts - min_attempts - 1, len(steps) - 1)
    return steps[idx]