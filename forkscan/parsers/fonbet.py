from typing import Dict, Optional, Set

import requests

from forkscan.core.sport_types import SportEvent
from forkscan.core.types import BookmakerName, EventManager, SportType


class FonbetParser:
    def __init__(self, event_manager: EventManager):
        self.manager = event_manager
        self.url = "https://line-lb11.bk6bba-resources.com/ma/events/list?lang=ru&version=52043578381&scopeMarket=1600"
        self.support_sports = {"football": SportType.FOOTBALL, "hockey": SportType.HOCKEY, "tennis": SportType.TENNIS,
                               "basketball": SportType.BASKETBALL, "table-tennis": SportType.TABLETENNIS,
                               "esports": SportType.ESPORTS}
        self.active_events: Set[str] = set()
        self.missing_events_counter: Dict[str, int] = {}
        self.known_factors = {
            # 921: "П1", 922: "X", 923: "П2", 924: "Тотал Больше", ...
        }

    @staticmethod
    def _create_event(
            bookmaker: BookmakerName,
            event_id: str,
            start_time: int,
            team1: str,
            team2: str,
            status: str,
            tournament_name: str,
            sport_type: SportType
    ) -> Optional[SportEvent]:
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
            return SportEvent.create(
                bookmaker=bookmaker,
                bookmaker_id=event_id,
                start_time=start_time,
                tournament_name=tournament_name,
                team1=team1,
                team2=team2,
                status=status,
                sport_type=sport_type
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
                              ) -> None:
        """Обработка одного события"""
        if not sport_data.get("name_sport") in self.support_sports:
            return

        status = "live" if event["place"] == "live" else "prematch"

        event = self._create_event(
            bookmaker=BookmakerName.FONBET,
            event_id=str(event["id"]),
            start_time=event["startTime"],
            tournament_name=sport_data["name_thournirer"],
            team1=event["team1"],
            team2=event["team2"],
            status=status,
            sport_type=self.support_sports.get(sport_data["name_sport"])
        )
        self.manager.add_event(event)

    def _update_events(self, new_event_ids: Set[str]) -> None:
        # Добавляем новые события в активные
        self.active_events |= new_event_ids

        # Найти события, которых нет в новых данных
        finished = self.active_events - new_event_ids

        # Увеличиваем счётчик для пропавших событий
        for event_id in finished:
            self.missing_events_counter[event_id] = self.missing_events_counter.get(event_id, 0) + 1
            # Удаляем событие, если оно пропало N раз подряд
            if self.missing_events_counter[event_id] >= 100:
                print(f"Delete: {event_id}")
                self.manager.remove_event_by_id(BookmakerName.FONBET, event_id)
                self.missing_events_counter.pop(event_id)
                self.active_events.discard(event_id)

        # Если событие снова появилось — сбрасываем счетчик
        for event_id in new_event_ids:
            if event_id in self.missing_events_counter:
                self.missing_events_counter.pop(event_id)

    def _fetch_data(self) -> tuple[list, list, list]:
        """Получает данные от API Fonbet"""
        response = requests.get(self.url, timeout=5).json()
        return response.get("events", []), response.get("sports", []), response.get("customFactors", [])

    def _decode_custom_factors(self, custom_factors_info, event_data, name_sport) -> None:
        """
        Для поддерживаемых видов спорта выводит id коэффициентов, которые не распознаны.
        """
        print("custom_factors_info", custom_factors_info)
        print("event_data", event_data)
        print("name_sport", name_sport)
        for factor_group in custom_factors_info:
            event_id = str(factor_group["e"])
            print("event_id", event_id)
            if event_id in event_to_sport:
                print("event_id213213", event_id)
                sport_name = event_to_sport[event_id]
                for factor in factor_group.get("factors", []):
                    factor_id = factor.get("f")
                    print("factor_id", factor_id)
                    if factor_id not in self.known_factors:
                        print(f"[{sport_name}] Unknown factor_id for event {event_id}: {factor_id}")

    def parse(self) -> None:
        """Основной метод парсинга"""
        try:
            events_info, sports_info, custom_factors_info = self._fetch_data()
            parent_dict = self._process_sports_info(sports_info)

            # Собираем реальные активные ID из пришедших событий, а не из customFactors
            new_event_ids: Set[str] = set()
            for event in events_info:
                if not self._is_valid_event(event):
                    continue

                evt_id = str(event["id"])
                sport_data = parent_dict.get(event.get("sportId", 0), {})
                if sport_data.get("name_sport") not in self.support_sports:
                    continue

                new_event_ids.add(evt_id)

                self._decode_custom_factors(custom_factors_info, event, sport_data["name_sport"])
                self._process_single_event(event, sport_data)
            self._update_events(new_event_ids)

        except requests.RequestException as e:
            print(f"Error fetching data from Fonbet: {e}")
        except Exception as e:
            print(f"Unexpected error processing Fonbet data: {e}")


# Пример использования:
if __name__ == "__main__":
    manager = EventManager()
    fonbet = FonbetParser(manager)
    import time

    while True:
        fonbet.parse()
        print('dsfadafsdaf')
        time.sleep(1)
    # Одиночный запуск
    # run_parser(manager)
    # print(f"Current events at {datetime.now(timezone.utc)}: {manager.get_all_events()}")

    # Для периодического запуска каждую секунду:
    # """
    # import time
    # while True:
    #     run_parser(manager)
    #     time.sleep(1)
    # """
