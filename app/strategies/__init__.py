"""Патерни стратегій для доменної логіки (наприклад, сортування подій)."""

from app.strategies.event_sort import (
    EventSortStrategy,
    SortByDeadline,
    SortByNewest,
    get_event_sort_strategy,
)

__all__ = [
    "EventSortStrategy",
    "SortByDeadline",
    "SortByNewest",
    "get_event_sort_strategy",
]
