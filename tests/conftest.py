from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timedelta
from typing import Generator

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUTO_CREATE_TABLES", "0")

from app import create_app, db as app_db
from app.models import User
from app.repositories.event_repository import InMemoryEventRepository
from tests.helpers import DummyUserForYou, DummyUserSubscriptions, make_event_stub


@pytest.fixture(scope="function")
def app() -> Generator:
    """Flask app with isolated in-memory SQLite per test."""
    application = create_app()
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False

    with application.app_context():
        from app import models  # noqa: F401
        from app.models import Category

        app_db.create_all()
        if Category.query.count() == 0:
            app_db.session.add(Category(name="SeedCatEvents"))
            app_db.session.add(Category(name="SeedCatGrants"))
            app_db.session.commit()

        yield application
        app_db.session.remove()
        app_db.drop_all()


@pytest.fixture
def client(app):
    """HTTP test client."""
    return app.test_client()


@pytest.fixture
def db(app):
    """App context for ``db.session`` during the test."""
    with app.app_context():
        yield app_db


@pytest.fixture
def user(app, db) -> User:
    """Unique user row for model or notification tests."""
    suffix = uuid.uuid4().hex[:8]
    u = User(
        username=f"u_{suffix}",
        email=f"{suffix}@example.com",
        role="user",
    )
    u.set_password("secret123")
    app_db.session.add(u)
    app_db.session.commit()
    return User.query.filter_by(username=f"u_{suffix}").first()


@pytest.fixture
def in_memory_event_repo() -> InMemoryEventRepository:
    """In-memory repository with a small mixed event set."""
    today = date.today()
    events = [
        make_event_stub(
            eid=1,
            title="Python Hackathon",
            deadline=today + timedelta(days=10),
            created_at=datetime(2024, 1, 2),
            category_id=1,
            format="offline",
            city="Львів",
        ),
        make_event_stub(
            eid=2,
            title="Data Science Meetup",
            deadline=today + timedelta(days=3),
            created_at=datetime(2024, 1, 5),
            category_id=2,
            format="online",
            city="Київ",
        ),
        make_event_stub(
            eid=3,
            title="Old pending",
            status="pending",
            deadline=today + timedelta(days=5),
            created_at=datetime(2023, 12, 1),
            category_id=1,
        ),
        make_event_stub(
            eid=4,
            title="Past deadline approved",
            status="approved",
            deadline=today - timedelta(days=1),
            created_at=datetime(2024, 1, 1),
            category_id=2,
        ),
        make_event_stub(
            eid=5,
            title="No deadline",
            deadline=None,
            created_at=datetime(2024, 2, 1),
            category_id=1,
            format="online",
            city="Одеса",
        ),
    ]
    return InMemoryEventRepository(events)


@pytest.fixture
def dummy_user_foryou_empty() -> DummyUserForYou:
    """Dummy user with empty interests and favorites (foryou feed)."""
    return DummyUserForYou()


@pytest.fixture
def dummy_user_subscriptions_empty() -> DummyUserSubscriptions:
    """Dummy user with no company or user subscriptions."""
    return DummyUserSubscriptions([], [])


@pytest.fixture
def reset_organization_approval_subject() -> Generator:
    """Reset organization approval observer singleton between tests."""
    import app.observers.organization_approval as org_mod

    org_mod._subject = None
    yield
    org_mod._subject = None
