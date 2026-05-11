from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from typing import Any, List


def make_event_stub(
    *,
    eid: int = 1,
    title: str = "Event",
    status: str = "approved",
    deadline: date | None = None,
    created_at: datetime | None = None,
    category_id: int | None = 1,
    company_id: int | None = None,
    author_id: int = 1,
    format: str | None = "online",
    city: str | None = "Київ",
) -> Any:
    return SimpleNamespace(
        id=eid,
        title=title,
        status=status,
        deadline=deadline,
        created_at=created_at or datetime(2024, 6, 1, 12, 0, 0),
        category_id=category_id,
        company_id=company_id,
        author_id=author_id,
        format=format,
        city=city,
    )


class _EmptyFavorites:
    def all(self) -> List[Any]:
        return []


class DummyUserForYou:
    is_authenticated = True

    def __init__(self) -> None:
        self.interests: List[Any] = []
        self.favorites = _EmptyFavorites()

    @property
    def subscribed_companies(self) -> List[Any]:
        return []

    @property
    def followed_users(self) -> Any:
        return SimpleNamespace(all=lambda: [])


class DummyUserSubscriptions:
    is_authenticated = True

    def __init__(self, companies: List[Any], followed: List[Any]) -> None:
        self.interests: List[Any] = []
        self._companies = companies
        self._followed = followed
        self.favorites = _EmptyFavorites()

    @property
    def subscribed_companies(self) -> List[Any]:
        return self._companies

    @property
    def followed_users(self) -> Any:
        return SimpleNamespace(all=lambda: self._followed)
