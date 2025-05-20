from abc import ABC
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Optional, Dict

from forkscan.core.types import SportType, BookmakerName


@dataclass
class EventIdentifiers:
    """Класс для хранения идентификаторов события у разных букмекеров"""
    bookmaker_ids: Dict[BookmakerName, str]  # {BookmakerName.WINLINE: "123", BookmakerName.FONBET: "456"}

    def add_bookmaker_id(self, bookmaker: BookmakerName, _id: str):
        self.bookmaker_ids[bookmaker] = _id

    def get_bookmaker_id(self, bookmaker: BookmakerName) -> Optional[str]:
        return self.bookmaker_ids.get(bookmaker)

    def has_bookmaker(self, bookmaker: BookmakerName) -> bool:
        return bookmaker in self.bookmaker_ids


@dataclass(kw_only=True)
class BaseSportEvent(ABC):
    """Базовый класс для всех спортивных событий"""
    identifiers: EventIdentifiers  # ID события у разных букмекеров
    event_name: str
    start_time: datetime
    sport_type: SportType
    league: str
    status: str  # live/prematch/finished
    score: Optional[str] = None
    current_period: Optional[str] = None

    @property
    def is_started(self) -> bool:
        return datetime.now(UTC) > self.start_time

    def add_bookmaker_data(self, bookmaker: BookmakerName, bookmaker_id: str):
        """Добавить идентификатор события у конкретного букмекера"""
        self.identifiers.add_bookmaker_id(bookmaker, bookmaker_id)


@dataclass
class FootballEvent(BaseSportEvent):
    home_team: str
    away_team: str
    first_half_score: Optional[str] = None
    yellow_cards: Optional[Dict[str, int]] = None
    red_cards: Optional[Dict[str, int]] = None
    corners: Optional[Dict[str, int]] = None

    @classmethod
    def create(cls,
               bookmaker: BookmakerName,
               bookmaker_id: str,
               event_name: str,
               start_time: datetime,
               league: str,
               home_team: str,
               away_team: str) -> 'FootballEvent':
        """Фабричный метод для создания события"""
        identifiers = EventIdentifiers(bookmaker_ids={bookmaker: bookmaker_id})
        return cls(
            identifiers=identifiers,
            event_name=event_name,
            start_time=start_time,
            sport_type=SportType.FOOTBALL,
            league=league,
            status="prematch",
            home_team=home_team,
            away_team=away_team
        )
