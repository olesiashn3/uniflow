"""Допоміжні функції для HTTP-інтеграційних тестів (без змін коду застосунку)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Optional, Tuple

from app.models import Category, Company, Event, User


def create_onboarded_user(db, *, password: str = "Secret123456") -> Tuple[User, str]:
    """Користувач з завершеним онбордингом (можна одразу логінити)."""
    suffix = uuid.uuid4().hex[:8]
    u = User(
        username=f"tu_{suffix}",
        email=f"{suffix}@example.com",
        role="user",
        onboarding_done=True,
    )
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return u, password


def create_admin_user(db, *, password: str = "AdminSecret99") -> Tuple[User, str]:
    suffix = uuid.uuid4().hex[:8]
    u = User(
        username=f"ad_{suffix}",
        email=f"adm_{suffix}@example.com",
        role="admin",
        onboarding_done=True,
    )
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return u, password


def login(client, email: str, password: str):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password, "submit": "1"},
        follow_redirects=True,
    )


def first_category_id(db) -> int:
    c = Category.query.order_by(Category.id).first()
    assert c is not None
    return c.id


def create_published_event(db, author: User, **kwargs) -> Event:
    """Схвалена подія з майбутнім дедлайном (видима на головній)."""
    defaults = dict(
        title="Published Integration Event",
        description="Опис події для інтеграційного тесту, довший за 20 символів.",
        requirements="",
        deadline=date.today() + timedelta(days=60),
        link=None,
        format="online",
        city="Київ",
        status="approved",
        author_id=author.id,
        category_id=first_category_id(db),
        company_id=None,
    )
    defaults.update(kwargs)
    e = Event(**defaults)
    db.session.add(e)
    db.session.commit()
    return e


def create_pending_event(db, author: User, **kwargs) -> Event:
    defaults = dict(
        title="Pending Route Event Title",
        description="Ще один довгий опис для валідації форми події.",
        requirements="",
        deadline=date.today() + timedelta(days=30),
        status="pending",
        author_id=author.id,
        category_id=first_category_id(db),
    )
    defaults.update(kwargs)
    e = Event(**defaults)
    db.session.add(e)
    db.session.commit()
    return e


def create_company(db, name: Optional[str] = None) -> Company:
    nm = name or f"Co_{uuid.uuid4().hex[:10]}"
    c = Company(name=nm[:100], description="d", is_verified=False)
    db.session.add(c)
    db.session.commit()
    return c
