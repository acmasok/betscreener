from abc import ABC, abstractmethod
from typing import Dict, Set, Optional, Type

import requests

from forkscan.core.types import (
    EventManager,
    FootballEvent,
    HockeyEvent,
    TennisEvent,
    BasketballEvent,
    TableTennisEvent,
    EsportsEvent,
    BookmakerName,
    BaseSportEvent
)


class BaseBookmakerParser(ABC):
    """Базовый класс для парсеров букмекерских контор"""

    def __init__(self, event_manager: EventManager):
        self.manager = event_manager
        self.support_sports = {"football", "hockey", "tennis", "basketball", "table-tennis", "esports"}
        self.active_events: Set[str] = set()

        # Маппинг для создания правильного типа события
        self.event_creators = {
            "football": (FootballEvent, self._create_sport_event),
            "hockey": (HockeyEvent, self._create_sport_event),
            "tennis": (TennisEvent, self._create_sport_event),
            "basketball": (BasketballEvent, self._create_sport_event),
            "table-tennis": (TableTennisEvent, self._create_sport_event),
            "esports": (EsportsEvent, self._create_sport_event)
        }

    @property
    @abstractmethod
    def bookmaker_name(self) -> BookmakerName:
        """Имя букмекера"""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Базовый URL для API букмекера"""
        pass

    def _create_sport_event(self,
                            event: Dict,
                            tournament_name: str,
                            event_class: Type[BaseSportEvent]) -> Optional[BaseSportEvent]:
        """
        Базовый метод создания спортивного события

        Args:
            event: Словарь с данными события
            tournament_name: Название турнира
            event_class: Класс создаваемого события

        Returns:
            Объект события если создание успешно, None если произошла ошибка
        """
        try:
            return event_class.create(
                bookmaker=self.bookmaker_name,
                bookmaker_id=self._get_event_id(event),
                start_time=self._get_start_time(event),
                tournament_name=tournament_name,
                team1=self._get_team1(event),
                team2=self._get_team2(event),
                status=self._get_event_status(event)
            )
        except KeyError as e:
            print(f"Missing required field in event data: {e}")
            return None
        except Exception as e:
            print(f"Error creating {event_class.__name__}: {e}")
            return None

    @abstractmethod
    def _get_event_id(self, event: Dict) -> str:
        """Получает ID события из данных букмекера"""
        pass

    @abstractmethod
    def _get_start_time(self, event: Dict) -> int:
        """Получает время начала события из данных букмекера"""
        pass

    @abstractmethod
    def _get_team1(self, event: Dict) -> str:
        """Получает название первой команды"""
        pass

    @abstractmethod
    def _get_team2(self, event: Dict) -> str:
        """Получает название второй команды"""
        pass

    @abstractmethod
    def _get_event_status(self, event: Dict) -> str:
        """Получает статус события"""
        pass

    @abstractmethod
    def _fetch_data(self) -> tuple[list, list]:
        """
        Получает данные от API букмекера

        Returns:
            Кортеж (список событий, список видов спорта)
        """
        pass

    @abstractmethod
    def _process_sports_info(self, sports_info: list) -> Dict[int, dict]:
        """
        Обработка информации о видах спорта

        Args:
            sports_info: Список спортивных данных от API

        Returns:
            Словарь с информацией о турнирах
        """
        pass

    @abstractmethod
    def _is_valid_event(self, event: Dict) -> bool:
        """
        Проверяет, является ли событие валидным для обработки

        Args:
            event: Словарь с данными события

        Returns:
            True если событие валидно, False если нет
        """
        pass

    def _process_single_event(self,
                              event: Dict,
                              sport_data: Dict,
                              new_event_ids: Set[str]) -> None:
        """
        Обработка одного события

        Args:
            event: Словарь с данными события
            sport_data: Словарь с данными о спорте
            new_event_ids: Множество для сбора новых ID событий
        """
        sport_name = sport_data.get("name_sport")
        if sport_name not in self.support_sports:
            return

        event_id = self._get_event_id(event)
        new_event_ids.add(event_id)

        if sport_name in self.event_creators:
            event_class, creator = self.event_creators[sport_name]
            sport_event = creator(event, sport_data["name_thournirer"], event_class)
            if sport_event:
                self.manager.add_event(sport_event)
        else:
            print(f"Unsupported sport type: {sport_name}")

    def _update_events(self, new_event_ids: Set[str]) -> None:
        """
        Обновляет список активных событий и удаляет завершенные

        Args:
            new_event_ids: Множество ID новых событий
        """
        finished_events = self.active_events - new_event_ids
        for event_id in finished_events:
            self.manager.remove_event_by_id(self.bookmaker_name, event_id)
        self.active_events = new_event_ids

    def parse(self) -> None:
        """Основной метод парсинга"""
        try:
            events_info, sports_info = self._fetch_data()
            parent_dict = self._process_sports_info(sports_info)
            new_event_ids: Set[str] = set()

            for event in events_info:
                if not self._is_valid_event(event):
                    continue

                sport_data = parent_dict.get(event.get("sportId", 0), {})
                self._process_single_event(event, sport_data, new_event_ids)

            self._update_events(new_event_ids)

        except requests.RequestException as e:
            print(f"Error fetching data from {self.bookmaker_name}: {e}")
        except Exception as e:
            print(f"Unexpected error processing {self.bookmaker_name} data: {e}")
