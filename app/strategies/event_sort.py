from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from app.models import Event


class EventSortStrategy(ABC):
    """Strategy for ordering public catalog events."""

    @abstractmethod
    def apply_sqlalchemy(self, query: Any) -> Any:
        """Apply ordering to a SQLAlchemy query."""

    @abstractmethod
    def apply_in_memory(self, events: List[Any]) -> List[Any]:
        """Return a new sorted list; do not mutate the input list."""


class SortByNewest(EventSortStrategy):
    """Order by ``created_at`` descending."""

    def apply_sqlalchemy(self, query: Any) -> Any:
        return query.order_by(Event.created_at.desc())

    def apply_in_memory(self, events: List[Any]) -> List[Any]:
        return sorted(events, key=lambda e: e.created_at, reverse=True)


class SortByDeadline(EventSortStrategy):
    """Events with a deadline only; earliest deadline first."""

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
    """Resolve strategy by ``sort`` query key; unknown keys map to ``SortByNewest``."""
    key = (sort_key or _DEFAULT_KEY).strip()
    return _SORT_REGISTRY.get(key, _SORT_REGISTRY[_DEFAULT_KEY])
