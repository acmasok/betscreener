from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum, auto
from typing import TypeAlias, TypedDict, List


class BookmakerName(Enum):
    """Поддерживаемые букмекеры."""

    WINLINE = auto()
    GGBET = auto()
    PARIMATCH = auto()
    FONBET = auto()
    ONE_WIN = auto()
    BETBOOM = auto()
    BETCITY = auto()
    LEON = auto()
    LIGASTAVOK = auto()
    MELBET = auto()
    OLIMPBET = auto()
    TENISI = auto()


class SportType(Enum):
    """Поддерживаемые виды спорта."""

    FOOTBALL = auto()
    BASKETBALL = auto()
    TENNIS = auto()
    HOCKEY = auto()
    CSGO = auto()
    DOTA2 = auto()


class MarketType(Enum):
    """
    Типы ставок в букмекерских конторах.

    Включает основные типы для футбола, баскетбола, тенниса и киберспорта.
    """

    # Исходы матча
    WIN_1 = auto()  # Победа первой команды
    DRAW = auto()  # Ничья
    WIN_2 = auto()  # Победа второй команды

    # Двойные шансы
    DOUBLE_1X = auto()  # Первая не проиграет
    DOUBLE_X2 = auto()  # Вторая не проиграет
    DOUBLE_12 = auto()  # Не будет ничьей

    # Тоталы
    TOTAL_OVER = auto()  # Тотал больше
    TOTAL_UNDER = auto()  # Тотал меньше

    # Форы
    HANDICAP_1 = auto()  # Фора первой команды
    HANDICAP_2 = auto()  # Фора второй команды

    # Индивидуальные тоталы
    TEAM_1_TOTAL_OVER = auto()  # Индивидуальный тотал первой больше
    TEAM_1_TOTAL_UNDER = auto()  # Индивидуальный тотал первой меньше
    TEAM_2_TOTAL_OVER = auto()  # Индивидуальный тотал второй больше
    TEAM_2_TOTAL_UNDER = auto()  # Индивидуальный тотал второй меньше

    # Счет по периодам (для баскетбола/киберспорта)
    PERIOD_1_WIN_1 = auto()  # Победа первой в 1 периоде
    PERIOD_1_DRAW = auto()  # Ничья в 1 периоде
    PERIOD_1_WIN_2 = auto()  # Победа второй в 1 периоде


@dataclass(frozen=True)
class MarketValue:
    """
    Значение рынка ставки.

    Attributes:
        market_type: Тип ставки
        value: Значение (для форы/тотала)
    """

    market_type: MarketType
    value: Decimal | None = None  # None для WIN/DRAW, Decimal для TOTAL/HANDICAP


Odds: TypeAlias = Decimal
Profit: TypeAlias = Decimal


class BetPosition(TypedDict):
    """
    Позиция ставки в вилке.

    Attributes:
        bookmaker: Название букмекера
        market: Тип ставки
        market_value: Значение ставки (например тотал 2.5)
        odds: Коэффициент
        recommended_stake: Рекомендуемая сумма ставки для оптимального распределения
        stake_limits: Ограничения на минимальную/максимальную ставку
    """

    bookmaker: BookmakerName
    market: MarketType
    market_value: MarketValue
    odds: Odds
    recommended_stake: Decimal
    stake_limits: tuple[Decimal, Decimal]  # min, max


class Fork(TypedDict):
    """
    Найденная вилка между букмекерами.

    Поддерживает мультивилки (3+ исхода).

    Attributes:
        sport: Вид спорта
        event_id: Уникальный идентификатор события
        event_name: Название события (например "Команда1 vs Команда2")
        start_time: Время начала события
        positions: Список позиций для ставок
        total_profit: Общая прибыль при оптимальном распределении ставок
        profit_percentage: Процент прибыли
        kelly_criterion: Критерий Келли для оценки оптимального размера ставки
        update_time: Время обновления коэффициентов
    """

    sport: SportType
    event_id: str
    event_name: str
    start_time: datetime
    positions: List[BetPosition]
    total_profit: Profit
    profit_percentage: Decimal
    kelly_criterion: Decimal
    update_time: datetime
