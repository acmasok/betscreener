from datetime import datetime, timezone
from typing import Dict, Set, Optional

import requests

from forkscan.core.types import EventManager, FootballEvent, BookmakerName


class FonbetParser:
    def __init__(self, event_manager: EventManager):
        self.manager = event_manager
        self.url = "https://line-lb11.bk6bba-resources.com/ma/events/list?lang=ru&version=52043578381&scopeMarket=1600"
        self.support_sports = {"football", "hockey", "tennis", "basketball", "table-tennis", "esports"}
        self.active_events: Set[str] = set()
        self.event_creators = {
            "football": self._create_football_event,
            "hockey": self._create_hockey_event,
            "tennis": self._create_tennis_event,
            "basketball": self._create_basketball_event,
            "table-tennis": self._create_table_tennis_event,
            "esports": self._create_esports_event
        }

    @staticmethod
    def _create_football_event(
            bookmaker: BookmakerName,
            event_id: str,
            start_time: int,
            team1: str,
            team2: str,
            status: str,
            tournament_name: str
    ) -> Optional[FootballEvent]:
        """
        Создает объект футбольного события из данных Fonbet

        Args:
            event_id: ID события
            start_time: Время начала события
            team1: Название первой команды
            team2: Название второй команды
            status: Место проведения события ('live' или другое значение для prematch)
            tournament_name: Название турнира

        Returns:
            FootballEvent если создание успешно, None если произошла ошибка
        """
        try:
            return FootballEvent.create(
                bookmaker=bookmaker,
                bookmaker_id=event_id,
                start_time=start_time,
                tournament_name=tournament_name,
                team1=team1,
                team2=team2,
                status=status
            )
        except Exception as e:
            print(f"Error creating football event: {e}")
            return None

    @staticmethod
    def _create_sports_lookup(sports_info: list) -> Dict[int, str]:
        """Создает словарь для поиска видов спорта"""
        return {
            sport["id"]: sport["alias"]
            for sport in sports_info
            if sport["kind"] == "sport"
        }

    @staticmethod
    def _create_tournaments_dict(sports_info: list, sports_lookup: Dict[int, str]) -> Dict[int, dict]:
        """Создает словарь турниров с информацией о виде спорта"""
        tournaments = {}

        for sport in sports_info:
            if sport["kind"] != "segment":
                continue

            parent_id = sport.get("parentId")
            if parent_id not in sports_lookup:
                continue

            tournaments[sport["id"]] = {
                "name_sport": sports_lookup[parent_id],
                "name_thournirer": sport["name"]
            }

        return tournaments

    def _process_sports_info(self, sports_info: list) -> Dict[int, dict]:
        """Обработка информации о видах спорта"""
        sports_lookup = self._create_sports_lookup(sports_info)
        return self._create_tournaments_dict(sports_info, sports_lookup)

    @staticmethod
    def _is_valid_event(event: dict) -> bool:
        """Проверяет, является ли событие валидным для обработки"""
        return (
                event.get("level") == 1 and
                event.get("kind") == 1 and
                not event.get("notMatch") and
                not event.get("noEventView") and
                event.get("place") != "notActive"
        )

    def _process_single_event(self,
                              event: dict,
                              sport_data: dict,
                              new_event_ids: set) -> None:
        """Обработка одного события"""
        if not sport_data.get("name_sport") in self.support_sports:
            return

        event_id = str(event["id"])
        new_event_ids.add(event_id)
        status = "live" if event["place"] == "live" else "prematch"

        football_event = self._create_football_event(
            bookmaker=BookmakerName.FONBET,
            event_id=str(event["id"]),
            start_time=event["startTime"],
            tournament_name=sport_data["name_thournirer"],
            team1=event["team1"],
            team2=event["team2"],
            status=status
        )
        if football_event:
            self.manager.add_event(football_event)

    def _update_events(self, new_event_ids: set) -> None:
        """Обновляет список активных событий и удаляет завершенные"""
        finished_events = self.active_events - new_event_ids
        for event_id in finished_events:
            self.manager.remove_event_by_id(BookmakerName.FONBET, event_id)
        self.active_events = new_event_ids

    def _fetch_data(self) -> tuple[list, list]:
        """Получает данные от API Fonbet"""
        response = requests.get(self.url, timeout=5).json()
        return response.get("events", []), response.get("sports", [])

    def parse(self) -> None:
        """Основной метод парсинга"""
        try:
            events_info, sports_info = self._fetch_data()
            parent_dict = self._process_sports_info(sports_info)
            new_event_ids = set()

            for event in events_info:
                if not self._is_valid_event(event):
                    continue

                sport_data = parent_dict.get(event.get("sportId", 0), {})
                self._process_single_event(event, sport_data, new_event_ids)

            self._update_events(new_event_ids)

        except requests.RequestException as e:
            print(f"Error fetching data from Fonbet: {e}")
        except Exception as e:
            print(f"Unexpected error processing Fonbet data: {e}")


def run_parser(manager: EventManager) -> None:
    """Функция для запуска парсера"""
    fonbet = FonbetParser(manager)
    fonbet.parse()


# Пример использования:
if __name__ == "__main__":
    manager = EventManager()

    # Одиночный запуск
    run_parser(manager)
    print(f"Current events at {datetime.now(timezone.utc)}: {manager.get_all_events()}")

    # Для периодического запуска каждую секунду:
    """
    import time
    while True:
        run_parser(manager)
        time.sleep(1)
    """
