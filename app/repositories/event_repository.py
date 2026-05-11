"""
Репозиторії подій: абстракція доступу до даних (принцип DIP / літера D з SOLID).

``SqlAlchemyEventRepository`` використовується в продакшені; ``InMemoryEventRepository`` —
для ізольованих тестів без БД.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from math import ceil
from typing import Any, Iterator, List, Optional

from sqlalchemy import or_

from app.models import Event
from app.strategies.event_sort import get_event_sort_strategy


class ListPagination:
    """
    Мінімальна імітація ``flask_sqlalchemy.Pagination`` для списків у пам'яті.

    Підтримує атрибути та методи, які використовує шаблон ``events/index.html``.
    """

    def __init__(self, items: List[Any], page: int, per_page: int, total: int) -> None:
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total

    @property
    def pages(self) -> int:
        if self.per_page == 0:
            return 0
        if self.total == 0:
            return 1
        return max(int(ceil(self.total / float(self.per_page))), 1)

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def prev_num(self) -> Optional[int]:
        return self.page - 1 if self.has_prev else None

    @property
    def next_num(self) -> Optional[int]:
        return self.page + 1 if self.has_next else None

    def iter_pages(
        self,
        left_edge: int = 2,
        right_edge: int = 2,
        left_current: int = 2,
        right_current: int = 2,
    ) -> Iterator[Optional[int]]:
        """Генерує номери сторінок і ``None`` як роздільники «…», за зразком Flask."""
        last = 0
        for num in range(1, self.pages + 1):
            if (
                num <= left_edge
                or (num > self.page - left_current - 1 and num < self.page + right_current)
                or num > self.pages - right_edge
            ):
                if last + 1 != num:
                    yield None
                yield num
                last = num


def _paginate_list(items: List[Any], page: int, per_page: int) -> ListPagination:
    per_page = per_page or 9
    page = max(1, page)
    total = len(items)
    start = (page - 1) * per_page
    chunk = items[start : start + per_page]
    return ListPagination(chunk, page, per_page, total)


class InMemoryPublicEventsResult:
    """Результат вибірки in-memory: підтримує ``.paginate()`` як SQLAlchemy ``Query``."""

    def __init__(self, events: List[Any]) -> None:
        self._events = events

    def paginate(self, page: int = 1, per_page: int = 9, error_out: bool = False) -> ListPagination:
        return _paginate_list(self._events, page, per_page)


class IEventRepository(ABC):
    """Інтерфейс репозиторію публічних (каталожних) подій."""

    @abstractmethod
    def build_public_events_query(
        self,
        search: str = "",
        category_id: int = 0,
        sort: str = "new",
        format_type: str = "",
        city_filter: str = "",
        feed: str = "all",
        user: Any = None,
    ) -> Any:
        """
        Будує вибірку схвалених майбутніх подій із фільтрами.

        Реалізація для SQLAlchemy повертає ``Query`` з ``.paginate()``.
        In-memory реалізація повертає ``InMemoryPublicEventsResult``.
        """


class SqlAlchemyEventRepository(IEventRepository):
    """Доступ до подій через ORM SQLAlchemy (основний шлях у застосунку)."""

    def build_public_events_query(
        self,
        search: str = "",
        category_id: int = 0,
        sort: str = "new",
        format_type: str = "",
        city_filter: str = "",
        feed: str = "all",
        user: Any = None,
    ) -> Any:
        query = Event.query.filter_by(status="approved")
        query = query.filter((Event.deadline >= date.today()) | (Event.deadline.is_(None)))

        if feed == "foryou" and user and getattr(user, "is_authenticated", False):
            interest_ids = [category.id for category in user.interests]
            favorites = user.favorites.all()
            activity_cat_ids = [
                fav.event.category_id for fav in favorites if fav.event and fav.event.category_id
            ]
            recommended_category_ids = list(set(interest_ids + activity_cat_ids))

            if recommended_category_ids:
                query = query.filter(Event.category_id.in_(recommended_category_ids))
            else:
                query = query.filter(Event.id < 0)
        elif feed == "subscriptions" and user and getattr(user, "is_authenticated", False):
            subscribed_company_ids = [company.id for company in user.subscribed_companies]
            followed_user_ids = [u.id for u in user.followed_users.all()]

            if subscribed_company_ids or followed_user_ids:
                parts = []
                if subscribed_company_ids:
                    parts.append(Event.company_id.in_(subscribed_company_ids))
                if followed_user_ids:
                    parts.append(Event.author_id.in_(followed_user_ids))

                if len(parts) == 1:
                    query = query.filter(parts[0])
                else:
                    query = query.filter(or_(*parts))
            else:
                query = query.filter(Event.id < 0)

        if search:
            query = query.filter(Event.title.ilike(f"%{search}%"))
        if category_id > 0:
            query = query.filter(Event.category_id == category_id)
        if format_type:
            query = query.filter_by(format=format_type)
        if city_filter:
            query = query.filter(Event.city.ilike(f"%{city_filter}%"))

        strategy = get_event_sort_strategy(sort)
        return strategy.apply_sqlalchemy(query)


def _in_memory_filter_feed(events: List[Any], feed: str, user: Any) -> List[Any]:
    if feed == "foryou" and user and getattr(user, "is_authenticated", False):
        interest_ids = [c.id for c in list(getattr(user, "interests", []) or [])]
        favorites = list(user.favorites.all()) if hasattr(user, "favorites") else []
        activity_cat_ids = [
            fav.event.category_id
            for fav in favorites
            if getattr(fav, "event", None) and getattr(fav.event, "category_id", None)
        ]
        recommended_category_ids = list(set(interest_ids + activity_cat_ids))
        if not recommended_category_ids:
            return []
        rid = set(recommended_category_ids)
        return [e for e in events if getattr(e, "category_id", None) in rid]

    if feed == "subscriptions" and user and getattr(user, "is_authenticated", False):
        subscribed_company_ids = [c.id for c in list(getattr(user, "subscribed_companies", []) or [])]
        followed_user_ids = (
            [u.id for u in user.followed_users.all()] if hasattr(user, "followed_users") else []
        )
        if not subscribed_company_ids and not followed_user_ids:
            return []

        def _match_subscription(ev: Any) -> bool:
            cid = getattr(ev, "company_id", None)
            aid = getattr(ev, "author_id", None)
            if subscribed_company_ids and cid in subscribed_company_ids:
                return True
            if followed_user_ids and aid in followed_user_ids:
                return True
            return False

        return [e for e in events if _match_subscription(e)]

    return events


class InMemoryEventRepository(IEventRepository):
    """
    Репозиторій подій у пам'яті (list об'єктів з атрибутами як у ``Event``).

    Логіка фільтрації узгоджена з ``SqlAlchemyEventRepository`` для режиму ``feed='all'``
    та основних полів; призначений для юніт-тестів.
    """

    def __init__(self, events: Optional[List[Any]] = None) -> None:
        self._events: List[Any] = list(events or [])

    def build_public_events_query(
        self,
        search: str = "",
        category_id: int = 0,
        sort: str = "new",
        format_type: str = "",
        city_filter: str = "",
        feed: str = "all",
        user: Any = None,
    ) -> InMemoryPublicEventsResult:
        today = date.today()
        rows = [
            e
            for e in self._events
            if getattr(e, "status", None) == "approved"
            and (getattr(e, "deadline", None) is None or getattr(e, "deadline") >= today)
        ]

        rows = _in_memory_filter_feed(rows, feed, user)

        if search:
            s = search.lower()
            rows = [e for e in rows if s in (getattr(e, "title", "") or "").lower()]
        if category_id > 0:
            rows = [e for e in rows if getattr(e, "category_id", None) == category_id]
        if format_type:
            rows = [e for e in rows if getattr(e, "format", None) == format_type]
        if city_filter:
            cf = city_filter.lower()
            rows = [e for e in rows if cf in (getattr(e, "city", "") or "").lower()]

        strategy = get_event_sort_strategy(sort)
        ordered = strategy.apply_in_memory(rows)
        return InMemoryPublicEventsResult(ordered)
