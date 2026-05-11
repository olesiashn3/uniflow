"""
Стратегії сортування подій у публічній стрічці (патерн Strategy).

Підтримуються застосування до SQLAlchemy-запиту та до списку об'єктів у пам'яті
(для in-memory репозиторія та тестів).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from app.models import Event


class EventSortStrategy(ABC):
    """Абстрактна стратегія сортування схвалених подій для каталогу."""

    @abstractmethod
    def apply_sqlalchemy(self, query: Any) -> Any:
        """Повертає запит SQLAlchemy з урахуванням обраного порядку."""

    @abstractmethod
    def apply_in_memory(self, events: List[Any]) -> List[Any]:
        """Повертає новий відсортований список подій (без зміни вхідного)."""


class SortByNewest(EventSortStrategy):
    """Сортування за датою створення: спочатку найновіші."""

    def apply_sqlalchemy(self, query: Any) -> Any:
        return query.order_by(Event.created_at.desc())

    def apply_in_memory(self, events: List[Any]) -> List[Any]:
        return sorted(events, key=lambda e: e.created_at, reverse=True)


class SortByDeadline(EventSortStrategy):
    """Лише події з дедлайном, найближчий дедлайн першим."""

    def apply_sqlalchemy(self, query: Any) -> Any:
        return query.filter(Event.deadline.isnot(None)).order_by(Event.deadline.asc())

    def apply_in_memory(self, events: List[Any]) -> List[Any]:
        with_deadline = [e for e in events if getattr(e, "deadline", None) is not None]
        return sorted(with_deadline, key=lambda e: e.deadline)


_DEFAULT_KEY = "new"

_SORT_REGISTRY: Dict[str, EventSortStrategy] = {
    "new": SortByNewest(),
    "deadline": SortByDeadline(),
}


def get_event_sort_strategy(sort_key: str) -> EventSortStrategy:
    """
    Фабрика стратегій сортування за рядковим ключем (як у query-параметрі ``sort``).

    Невідомі значення відкочуються до ``SortByNewest``.
    """
    key = (sort_key or _DEFAULT_KEY).strip()
    return _SORT_REGISTRY.get(key, _SORT_REGISTRY[_DEFAULT_KEY])
