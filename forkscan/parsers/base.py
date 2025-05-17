from abc import ABC, abstractmethod
from datetime import datetime
from typing import AsyncIterator, Optional

from forkscan.core.types import BookmakerName, MarketType, Odds, SportType

class BaseParser(ABC):
    """Базовый класс для парсеров букмекерских контор."""

    def __init__(self, bookmaker: BookmakerName, api_key: Optional[str] = None) -> None:
        """
        Инициализация парсера.

        Args:
            bookmaker: Название букмекерской конторы
            api_key: API ключ для доступа к API букмекера
        """
        self.bookmaker = bookmaker
        self.api_key = api_key
        self._session = None

    @abstractmethod
    async def connect(self) -> None:
        """Установить соединение с API букмекера."""
        pass

    @abstractmethod
    async def get_odds(
        self,
        sport: SportType,
        market: MarketType,
        from_date: datetime,
        to_date: datetime
    ) -> AsyncIterator[tuple[str, Odds]]:
        """
        Получить коэффициенты для указанного события.

        Args:
            sport: Вид спорта
            market: Тип ставки
            from_date: Начальная дата
            to_date: Конечная дата

        Yields:
            tuple[str, Odds]: Пара (название события, коэффициент)
        """
        pass

    @abstractmethod
    async def validate_odds(self, event_name: str, market: MarketType, odds: Odds) -> bool:
        """
        Проверить актуальность коэффициента.

        Args:
            event_name: Название события
            market: Тип ставки
            odds: Коэффициент для проверки

        Returns:
            bool: True если коэффициент все еще актуален
        """
        pass