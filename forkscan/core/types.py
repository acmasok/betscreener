import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, Generic, Optional, Tuple, TypeVar
from unicodedata import normalize


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
    ESPORTS = auto()
    TABLETENNIS = auto()


class EventStatus(Enum):
    PREMATCH = "prematch"
    LIVE = "live"
    FINISHED = "finished"


T = TypeVar("T", bound="BaseSportEvent")


@dataclass(frozen=True)
class EventKey:
    teams: Tuple[str, str]

    def __str__(self) -> str:
        return f"EventKey(teams='{self.teams[0]}' vs '{self.teams[1]}')"

    @classmethod
    def create(cls, team1: str, team2: str) -> "EventKey":
        if not team1 or not team2:
            raise ValueError(f"Team names cannot be empty: team1='{team1}', team2='{team2}'")

        normalized_teams = sorted(
            [cls._normalize_team_name(team1), cls._normalize_team_name(team2)]
        )

        return cls(tuple(normalized_teams))

    @staticmethod
    def _normalize_team_name(name: str) -> str:
        """Нормализует название команды/игрока"""
        if not name:
            raise ValueError(f"Team name cannot be empty: '{name}'")

        # Приводим к нижнему регистру
        name = name.lower()

        # Создаем словарь для транслитерации русских букв
        ru_en = {
            "а": "a",
            "б": "b",
            "в": "v",
            "г": "g",
            "д": "d",
            "е": "e",
            "ё": "e",
            "ж": "zh",
            "з": "z",
            "и": "i",
            "й": "y",
            "к": "k",
            "л": "l",
            "м": "m",
            "н": "n",
            "о": "o",
            "п": "p",
            "р": "r",
            "с": "s",
            "т": "t",
            "у": "u",
            "ф": "f",
            "х": "h",
            "ц": "ts",
            "ч": "ch",
            "ш": "sh",
            "щ": "sch",
            "ъ": "",
            "ы": "y",
            "ь": "",
            "э": "e",
            "ю": "yu",
            "я": "ya",
        }

        # Транслитерация русских букв
        name = "".join(ru_en.get(c, c) for c in name)

        # Убираем диакритические знаки с латинских букв
        name = normalize("NFKD", name).encode("ASCII", "ignore").decode("ASCII")

        # Оставляем только буквы и цифры
        name = re.sub(r"[^a-z0-9]", "", name)

        return name


@dataclass
class EventNormalizer(Generic[T], ABC):
    """Абстрактный класс для нормализации данных от разных букмекеров"""

    bookmaker: BookmakerName

    @abstractmethod
    def normalize(self, raw_data: Dict[str, Any]) -> T:
        """Преобразует сырые данные букмекера в unified формат"""
        pass


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


@dataclass(kw_only=True)
class BaseSportEvent(ABC):
    """Базовый класс для всех спортивных событий"""

    bookmaker_id: str  # ID события у конкретного букмекера
    start_time: datetime
    sport_type: SportType
    event_name: str
    league: str
    status: EventStatus
    bookmaker: BookmakerName

    @property
    def is_started(self) -> bool:
        return datetime.now(UTC) > self.start_time

    @abstractmethod
    def create_key(self) -> EventKey:
        """Создает ключ для сопоставления событий между букмекерами"""
        pass


@dataclass
class FootballEvent(BaseSportEvent):
    team1: str
    team2: str

    def create_key(self) -> EventKey:
        return EventKey.create(self.team1, self.team2)

    @staticmethod
    def _convert_status(status: str) -> EventStatus:
        """Преобразует статус из формата букмекера в наш формат"""
        status_map = {"prematch": EventStatus.PREMATCH, "live": EventStatus.LIVE}
        return status_map.get(status.lower(), EventStatus.PREMATCH)

    @classmethod
    def create(
        cls,
        bookmaker: BookmakerName,
        bookmaker_id: str,
        start_time: int,
        tournament_name: str,
        team1: str,
        team2: str,
        status: str,
    ) -> "FootballEvent":  # Добавили параметр status
        return cls(
            bookmaker_id=bookmaker_id,
            event_name=f"{team1} - {team2}",
            start_time=datetime.fromtimestamp(start_time, timezone.utc),
            sport_type=SportType.FOOTBALL,
            league=tournament_name,
            status=cls._convert_status(status),  # Преобразуем входящий статус
            bookmaker=bookmaker,
            team1=team1,
            team2=team2,
        )


@dataclass
class EventManager:
    """Менеджер для управления событиями"""

    events: Dict[EventKey, Dict[BookmakerName, BaseSportEvent]] = field(default_factory=dict)
    normalizers: Dict[BookmakerName, Dict[SportType, EventNormalizer]] = field(default_factory=dict)

    def add_event(self, event: BaseSportEvent) -> BaseSportEvent:
        """Добавляет событие в менеджер"""
        try:
            event_key = event.create_key()
            if event_key not in self.events:
                self.events[event_key] = {}
            self.events[event_key][event.bookmaker] = event
            return event
        except ValueError as e:
            print(f"Failed to add event: {e}")
            print(f"Event data: {event}")
            raise

    def get_event(self, event_key: EventKey, bookmaker: BookmakerName) -> Optional[BaseSportEvent]:
        """Получает событие по ключу и букмекеру"""
        return self.events.get(event_key, {}).get(bookmaker)

    def get_same_events(self, event: BaseSportEvent) -> Dict[BookmakerName, BaseSportEvent]:
        """Получает одно и то же событие у разных букмекеров"""
        event_key = event.create_key()
        return self.events.get(event_key, {})

    def get_all_events(self) -> Dict[EventKey, Dict[BookmakerName, BaseSportEvent]]:
        """Получает все события"""
        return self.events

    def remove_event_by_id(self, bookmaker: BookmakerName, bookmaker_id: str) -> None:
        """Удаляет событие по ID букмекера"""
        # Находим все ключи событий
        keys_to_remove = []
        for event_key, bookmaker_events in self.events.items():
            if (
                bookmaker in bookmaker_events
                and bookmaker_events[bookmaker].bookmaker_id == bookmaker_id
            ):
                if len(bookmaker_events) == 1:
                    # Если это единственное событие для данного ключа,
                    # помечаем весь ключ на удаление
                    keys_to_remove.append(event_key)
                else:
                    # Иначе удаляем только событие конкретного букмекера
                    del bookmaker_events[bookmaker]

        # Удаляем помеченные ключи
        for key in keys_to_remove:
            print("Пропало событие", self.events[key])
            del self.events[key]
