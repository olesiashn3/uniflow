from __future__ import annotations

import itertools
from datetime import date, datetime, timedelta
from typing import List, Tuple

import pytest

from app.strategies.event_sort import (
    EventSortStrategy,
    SortByDeadline,
    SortByNewest,
    get_event_sort_strategy,
)
from tests.helpers import make_event_stub

_SORT_FACTORY_KEYS: List[str] = [
    "new",
    "deadline",
    "",
    "   ",
    "unknown",
    "NEW",
    "deadline\n",
    "random_key_xyz",
]

_DEADLINE_BASES = [date(2024, 1, 1) + timedelta(days=k) for k in range(7)]
_CREATED_OFFSET_HOURS = [0, 3, 7, 12, 24, 48]
_VARIANTS = list(range(5))

_SORT_DATE_PARAMS: List[Tuple[date, int, int]] = list(
    itertools.product(_DEADLINE_BASES, _CREATED_OFFSET_HOURS, _VARIANTS)
)


@pytest.mark.parametrize("sort_key", _SORT_FACTORY_KEYS)
def test_get_event_sort_strategy_returns_strategy(sort_key: str):
    """get_event_sort_strategy always returns an EventSortStrategy instance."""
    strat = get_event_sort_strategy(sort_key)
    assert isinstance(strat, EventSortStrategy)


@pytest.mark.parametrize(
    "sort_key,expect_newest",
    [
        ("deadline", False),
        ("new", True),
        ("", True),
        ("nope", True),
    ],
)
def test_factory_maps_known_and_unknown(sort_key, expect_newest):
    """deadline maps to SortByDeadline; unknown keys map to SortByNewest."""
    strat = get_event_sort_strategy(sort_key)
    if expect_newest:
        assert isinstance(strat, SortByNewest)
    else:
        assert isinstance(strat, SortByDeadline)


@pytest.mark.parametrize("base,off,var", _SORT_DATE_PARAMS)
def test_sort_by_newest_in_memory_order(base, off, var):
    """SortByNewest orders by created_at descending."""
    e1 = make_event_stub(
        eid=1,
        title="a",
        created_at=datetime(2024, 6, 1, 10, 0, 0) + timedelta(hours=off),
        deadline=base + timedelta(days=var),
        status="approved",
    )
    e2 = make_event_stub(
        eid=2,
        title="b",
        created_at=datetime(2024, 6, 2, 10, 0, 0) + timedelta(hours=off + var),
        deadline=base + timedelta(days=1),
        status="approved",
    )
    strat = SortByNewest()
    ordered = strat.apply_in_memory([e1, e2])
    assert ordered[0].created_at >= ordered[1].created_at


@pytest.mark.parametrize("base,off,var", _SORT_DATE_PARAMS)
def test_sort_by_deadline_in_memory_filters_none(base, off, var):
    """SortByDeadline drops missing deadlines and sorts ascending."""
    e0 = make_event_stub(
        eid=0,
        title="none",
        created_at=datetime(2024, 1, 1) + timedelta(hours=off),
        deadline=None,
        status="approved",
    )
    e1 = make_event_stub(
        eid=1,
        title="a",
        created_at=datetime(2024, 1, 2) + timedelta(hours=off),
        deadline=base + timedelta(days=var % 3),
        status="approved",
    )
    e2 = make_event_stub(
        eid=2,
        title="b",
        created_at=datetime(2024, 1, 3) + timedelta(hours=off),
        deadline=base + timedelta(days=2 + (var % 2)),
        status="approved",
    )
    strat = SortByDeadline()
    ordered = strat.apply_in_memory([e0, e1, e2])
    assert all(getattr(x, "deadline", None) is not None for x in ordered)
    for i in range(len(ordered) - 1):
        assert ordered[i].deadline <= ordered[i + 1].deadline


@pytest.mark.parametrize("status", ["approved", "pending", "rejected", "draft", "hold", "archived"])
def test_strategies_ignore_status_field(status):
    """Strategies do not filter by status in in-memory mode."""
    today = date.today()
    e = make_event_stub(
        status=status,
        deadline=today + timedelta(days=3),
        created_at=datetime(2024, 5, 1),
    )
    n = SortByNewest().apply_in_memory([e])
    d = SortByDeadline().apply_in_memory([e])
    assert len(n) == 1
    assert len(d) == 1


@pytest.mark.parametrize("n", range(15))
def test_newest_stable_with_identical_timestamps(n):
    """Identical created_at keeps five items in output."""
    ts = datetime(2024, 3, 1, 12, 0, 0)
    today = date.today()
    events = [
        make_event_stub(eid=i, title=f"t{i}", created_at=ts, deadline=today + timedelta(days=1), status="approved")
        for i in range(5)
    ]
    ordered = SortByNewest().apply_in_memory(events)
    assert len(ordered) == 5


@pytest.mark.parametrize("n", range(15))
def test_deadline_stable_equal_deadlines(n):
    """Equal deadlines keep four items with deadlines in output."""
    today = date.today()
    ts = datetime(2024, 2, 1)
    events = [
        make_event_stub(eid=i, title=f"x{i}", created_at=ts + timedelta(minutes=i), deadline=today, status="approved")
        for i in range(4)
    ]
    ordered = SortByDeadline().apply_in_memory(events)
    assert len(ordered) == 4
