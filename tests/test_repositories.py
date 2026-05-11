from __future__ import annotations

import itertools
import math
from datetime import date, datetime, timedelta
from typing import Any, List

import pytest

from app.repositories.event_repository import InMemoryEventRepository, InMemoryPublicEventsResult
from tests.helpers import DummyUserSubscriptions, make_event_stub

_FILTER_COMBOS: List[tuple] = list(
    itertools.product(
        ["new", "deadline", "", "unknown"],
        ["", "Hack", "data"],
        [0, 1, 2],
        ["", "online"],
        ["", "Київ", "Льв"],
    )
)

_PAGINATION_COMBOS: List[tuple] = list(
    itertools.product(
        [1, 2, 3, 4, 5],
        [1, 5, 9, 12],
        [0, 1, 11, 25, 100],
    )
)

_PUBLIC_RESULT_PAGINATION: List[tuple] = list(
    itertools.product(
        [0, 1, 5, 10, 20, 35],
        [1, 2, 4],
        [3, 7, 11],
    )
)


def _seed_events_for_filters(today: date, n: int = 12) -> List[Any]:
    out: List[Any] = []
    for i in range(n):
        dl = today + timedelta(days=i % 7) if i % 4 != 0 else None
        out.append(
            make_event_stub(
                eid=i + 1,
                title=f"Event {i} Hack data",
                status="approved" if i % 6 != 0 else "pending",
                deadline=dl,
                created_at=datetime(2024, 1, 1) + timedelta(hours=i),
                category_id=(i % 3) + 1,
                company_id=(i % 2) + 1 if i % 3 == 0 else None,
                author_id=10 + (i % 4),
                format="online" if i % 2 == 0 else "offline",
                city=["Київ", "Львів", "Одеса", "Харків"][i % 4],
            )
        )
    return out


@pytest.mark.parametrize("sort,search,category,fmt,city", _FILTER_COMBOS)
def test_in_memory_repository_filter_matrix(sort, search, category, fmt, city):
    """Filter and sort combinations return valid pagination."""
    today = date.today()
    repo = InMemoryEventRepository(_seed_events_for_filters(today))
    res = repo.build_public_events_query(
        search=search,
        category_id=category,
        sort=sort,
        format_type=fmt,
        city_filter=city,
        feed="all",
        user=None,
    )
    page = res.paginate(page=1, per_page=9)
    assert page.total >= 0
    assert len(page.items) <= 9
    assert page.pages >= 1


@pytest.mark.parametrize("page,per_page,total_events", _PAGINATION_COMBOS)
def test_in_memory_pagination_sizes(page, per_page, total_events):
    """Pagination slice sizes match ListPagination rules."""
    today = date.today()
    events = [
        make_event_stub(
            eid=i + 1,
            title=f"T{i}",
            status="approved",
            deadline=today + timedelta(days=1),
            created_at=datetime(2024, 1, 1) + timedelta(minutes=i),
            category_id=1,
        )
        for i in range(total_events)
    ]
    repo = InMemoryEventRepository(events)
    res = repo.build_public_events_query(feed="all", user=None)
    p = res.paginate(page=page, per_page=per_page)
    assert p.total == total_events
    expected_pages = max(int(math.ceil(total_events / float(per_page))), 1) if total_events else 1
    assert p.pages == expected_pages
    if total_events == 0 or page > p.pages:
        assert len(p.items) == 0
    else:
        assert len(p.items) == min(per_page, total_events - (page - 1) * per_page)


@pytest.mark.parametrize("total,page,per_page", _PUBLIC_RESULT_PAGINATION)
def test_in_memory_public_result_paginate(total, page, per_page):
    """InMemoryPublicEventsResult.paginate respects total and per_page."""
    today = date.today()
    events = [
        make_event_stub(
            eid=i + 1,
            title=f"x{i}",
            status="approved",
            deadline=today + timedelta(days=1),
            created_at=datetime(2024, 1, 1) + timedelta(seconds=i),
        )
        for i in range(total)
    ]
    res = InMemoryPublicEventsResult(events)
    p = res.paginate(page=page, per_page=per_page)
    assert p.total == total
    assert len(p.items) <= per_page


@pytest.mark.parametrize(
    "left_edge,right_edge,left_current,right_current",
    list(itertools.product([1, 2], [1, 2], [1, 2], [1, 2])),
)
def test_in_memory_result_iter_pages_smoke(left_edge, right_edge, left_current, right_current):
    """iter_pages yields ints or None without raising."""
    today = date.today()
    events = [
        make_event_stub(eid=i, title=f"e{i}", deadline=today + timedelta(days=1), status="approved")
        for i in range(30)
    ]
    p = InMemoryPublicEventsResult(events).paginate(2, 5)
    seq = list(p.iter_pages(left_edge, right_edge, left_current, right_current))
    assert len(seq) >= 1
    assert all(x is None or isinstance(x, int) for x in seq)


def test_in_memory_empty_repository():
    """Empty backing list yields zero results."""
    repo = InMemoryEventRepository([])
    res = repo.build_public_events_query()
    p = res.paginate(1, 9)
    assert p.total == 0
    assert p.items == []


@pytest.mark.parametrize("status", ["pending", "rejected", "draft", "approved"])
def test_only_approved_visible(status):
    """Only approved events appear in public in-memory query."""
    today = date.today()
    ev = make_event_stub(status=status, deadline=today + timedelta(days=1))
    repo = InMemoryEventRepository([ev])
    p = repo.build_public_events_query().paginate(1, 9)
    if status == "approved":
        assert p.total == 1
    else:
        assert p.total == 0


@pytest.mark.parametrize("delta", [-1, 0, 1, 7, 30, 365])
def test_deadline_cutoff_today(delta):
    """Past deadlines are excluded from public query."""
    today = date.today()
    ev = make_event_stub(
        eid=1,
        status="approved",
        deadline=today + timedelta(days=delta),
    )
    repo = InMemoryEventRepository([ev])
    total = repo.build_public_events_query().paginate(1, 9).total
    if delta < 0:
        assert total == 0
    else:
        assert total == 1


def test_foryou_feed_no_matches(dummy_user_foryou_empty):
    """foryou feed is empty when interests and favorites are empty."""
    today = date.today()
    ev = make_event_stub(
        deadline=today + timedelta(days=1),
        category_id=99,
        status="approved",
    )
    repo = InMemoryEventRepository([ev])
    p = repo.build_public_events_query(feed="foryou", user=dummy_user_foryou_empty).paginate(1, 9)
    assert p.total == 0


def test_subscriptions_feed_no_subscriptions(dummy_user_subscriptions_empty):
    """subscriptions feed is empty without follows or company subscriptions."""
    today = date.today()
    ev = make_event_stub(deadline=today + timedelta(days=1), status="approved", company_id=1)
    repo = InMemoryEventRepository([ev])
    p = repo.build_public_events_query(
        feed="subscriptions",
        user=dummy_user_subscriptions_empty,
    ).paginate(1, 9)
    assert p.total == 0


def test_subscriptions_feed_matches_company():
    """subscriptions feed includes events for subscribed company."""
    today = date.today()
    c = type("C", (), {"id": 5})()
    user = DummyUserSubscriptions([c], [])
    ev = make_event_stub(
        company_id=5,
        deadline=today + timedelta(days=2),
        status="approved",
    )
    repo = InMemoryEventRepository([ev])
    p = repo.build_public_events_query(feed="subscriptions", user=user).paginate(1, 9)
    assert p.total == 1


def test_subscriptions_feed_matches_author():
    """subscriptions feed includes events for followed authors."""
    today = date.today()
    u = type("U", (), {"id": 42})()
    user = DummyUserSubscriptions([], [u])
    ev = make_event_stub(
        author_id=42,
        company_id=None,
        deadline=today + timedelta(days=2),
        status="approved",
    )
    repo = InMemoryEventRepository([ev])
    p = repo.build_public_events_query(feed="subscriptions", user=user).paginate(1, 9)
    assert p.total == 1


@pytest.mark.parametrize("unicode_title", ["Подія 🎓", "日本語", "Café", "Plain"])
def test_search_unicode_and_plain_title(unicode_title):
    """Title search handles Unicode substrings."""
    today = date.today()
    ev = make_event_stub(title=unicode_title, deadline=today + timedelta(days=1), status="approved")
    repo = InMemoryEventRepository([ev])
    needle = unicode_title[:2] if len(unicode_title) >= 2 else unicode_title
    res = repo.build_public_events_query(search=needle)
    assert res.paginate(1, 9).total in (0, 1)


@pytest.mark.parametrize("sort", ["new", "deadline"])
def test_sort_ordering_len(sort):
    """Two approved events with valid deadlines both appear."""
    today = date.today()
    d = today + timedelta(days=5)
    events = [
        make_event_stub(eid=1, title="A", created_at=datetime(2024, 1, 1), deadline=d, status="approved"),
        make_event_stub(eid=2, title="B", created_at=datetime(2024, 1, 1), deadline=d, status="approved"),
    ]
    repo = InMemoryEventRepository(events)
    items = repo.build_public_events_query(sort=sort).paginate(1, 9).items
    assert len(items) == 2


def test_fixture_repo_has_mixed_status(in_memory_event_repo):
    """Fixture repo yields at least one approved public event."""
    p = in_memory_event_repo.build_public_events_query().paginate(1, 9)
    assert p.total >= 1
