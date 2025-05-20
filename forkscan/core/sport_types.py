from dataclasses import dataclass
from datetime import datetime, timezone

from forkscan.core.types import BaseSportEvent, BookmakerName, EventKey, EventStatus, SportType


@dataclass
class SportEvent(BaseSportEvent):
    """Универсальный класс события для всех поддерживаемых видов спорта."""

    team1: str
    team2: str

    def create_key(self) -> EventKey:
        """Создаёт уникальный ключ события на основе названий команд."""
        return EventKey.create(self.team1, self.team2)

    @staticmethod
    def _convert_status(status: str) -> EventStatus:
        """Преобразует статус из формата букмекера в наш формат."""
        status_map = {
            "prematch": EventStatus.PREMATCH,
            "live": EventStatus.LIVE,
            "finished": EventStatus.FINISHED,
        }
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
        sport_type: SportType,
        status: str,
    ) -> "SportEvent":
        """Создаёт объект события для указанного вида спорта.

        Args:
            bookmaker (BookmakerName): имя букмекера.
            bookmaker_id (str): внутренний идентификатор события у букмекера.
            start_time (int): время начала в формате UNIX timestamp.
            tournament_name (str): название турнира или лиги.
            team1 (str): первая команда / игрок.
            team2 (str): вторая команда / игрок.
            sport_type (SportType): тип спорта из Enum SportType.
            status (str): статус матча в формате букмекера.

        Returns:
            SportEvent: экземпляр универсального события.
        """
        return cls(
            bookmaker_id=bookmaker_id,
            event_name=f"{team1} vs {team2}",
            start_time=datetime.fromtimestamp(start_time, timezone.utc),
            sport_type=sport_type,
            league=tournament_name,
            status=cls._convert_status(status),
            bookmaker=bookmaker,
            team1=team1,
            team2=team2,
        )
