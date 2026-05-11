"""
Тести моделей ORM (SQLite in-memory): паролі, унікальність, обмеження довжин, repr.

Валідація email як політика тестового шару (regex), оскільки ORM не валідує формат.
"""

from __future__ import annotations

import itertools
import re
import uuid
from typing import Tuple

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Company, Event, User

# 10*6 = 60 комбінацій локальної частини та домену
_EMAIL_PARTS: list[Tuple[str, str]] = list(
    itertools.product(
        ["user", "a", "test.name", "user+tag", "u_1", "_lead", "bot", "qa", "st", "z9"],
        ["example.com", "sub.domain.org", "mail.io", "localhost", "xn--test.com", "corp.dev"],
    )
)

# Додаткові «крайні» адреси (довжина / символи)
_EXTRA_EMAILS = [
    "a@b.co",
    "long+" + "x" * 40 + "@example.com",
    "юзер@example.com",
    "user@тест.укр",
    " " + "trim@example.com",  # пробіл на початку — зберігається як є в БД
]

# Довжини паролів для set_password / check_password
_PASSWORD_LENGTHS = list(range(0, 35)) + [40, 64, 100, 255]

_LOOSE_EMAIL_RE = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
)


@pytest.mark.parametrize("local,domain", _EMAIL_PARTS)
def test_user_email_roundtrip_storage(app, db, local, domain):
    """Email зберігається та читається з БД; довжина вкладена в обмеження колонок."""
    email = f"{local}@{domain}"
    if len(email) > 120 or len(local) + len(domain) + 1 > 120:
        pytest.skip("довжина за межами String(120)")
    suffix = uuid.uuid4().hex[:6]
    u = User(username=f"em_{suffix}_{local[:8]}", email=email, role="user")
    u.set_password("pw")
    db.session.add(u)
    db.session.commit()
    loaded = User.query.filter_by(email=email).first()
    assert loaded is not None
    assert loaded.email == email


@pytest.mark.parametrize("raw", _EXTRA_EMAILS)
def test_user_extra_email_strings(app, db, raw):
    """Додаткові рядки email: commit або skip за довжиною username/email."""
    if len(raw) > 120:
        pytest.skip("email too long")
    suffix = uuid.uuid4().hex[:8]
    username = f"ex_{suffix}"[:64]
    u = User(username=username, email=raw.strip() if raw.startswith(" ") else raw, role="user")
    u.set_password("secret")
    db.session.add(u)
    db.session.commit()
    assert User.query.filter_by(username=username).first() is not None


_LOOSE_CASES = [
    ("good@example.com", True),
    ("bad", False),
    ("no-at-sign.com", False),
    ("@nodomain.com", False),
    ("double@@bad.com", False),
    ("ok+tag@sub.example.co.uk", True),
    ("u@x.co", True),
    ("", False),
    ("spaces in@bad.com", False),
] + [(f"auto{i}@generated.test", True) for i in range(42)]


@pytest.mark.parametrize("email,expect_pattern", _LOOSE_CASES)
def test_loose_email_pattern_examples(email, expect_pattern):
    """Документована політика «схоже на email» для тестових даних."""
    assert bool(_LOOSE_EMAIL_RE.search(email.strip())) == expect_pattern


@pytest.mark.parametrize("length", _PASSWORD_LENGTHS)
def test_user_password_length_roundtrip(app, db, length):
    """``set_password`` / ``check_password`` для різних довжин."""
    suffix = uuid.uuid4().hex[:8]
    u = User(username=f"pw_{suffix}", email=f"{suffix}@e.com", role="user")
    raw = "" if length == 0 else ("p" * length)
    u.set_password(raw)
    db.session.add(u)
    db.session.commit()
    again = User.query.filter_by(username=f"pw_{suffix}").first()
    assert again.check_password(raw)


@pytest.mark.parametrize("n", range(20))
def test_user_repr_contains_username(app, db, n):
    """``__repr__`` містить username."""
    suffix = uuid.uuid4().hex[:8]
    name = f"repr_{n}_{suffix}"[:64]
    u = User(username=name, email=f"{suffix}{n}@e.com", role="user")
    u.set_password("x")
    db.session.add(u)
    db.session.commit()
    assert name in repr(u)


@pytest.mark.parametrize("title_len", [1, 50, 100, 199, 200])
def test_event_title_boundary(app, db, user, title_len):
    """Подія з title довжиною до 200 символів зберігається."""
    t = ("T" * title_len)[:200]
    e = Event(
        title=t,
        description="d" * 10,
        author_id=user.id,
        status="pending",
    )
    db.session.add(e)
    db.session.commit()
    assert Event.query.get(e.id).title == t


@pytest.mark.parametrize("status", ["pending", "approved", "rejected"])
def test_event_status_values(app, db, user, status):
    """Дозволені рядкові статуси події зберігаються."""
    e = Event(
        title="S",
        description="body",
        author_id=user.id,
        status=status,
    )
    db.session.add(e)
    db.session.commit()
    assert Event.query.get(e.id).status == status


@pytest.mark.parametrize("nlen", [1, 50, 99, 100])
def test_company_name_lengths(app, db, nlen):
    """Назва компанії до 100 символів."""
    name = ("C" * nlen) + uuid.uuid4().hex[:6]
    name = name[:100]
    c = Company(name=name, description=None)
    db.session.add(c)
    db.session.commit()
    assert Company.query.filter_by(name=name).first() is not None


def test_duplicate_username_raises(app, db):
    """Унікальність username."""
    suffix = uuid.uuid4().hex[:8]
    a = User(username=f"d_{suffix}", email=f"a_{suffix}@e.com", role="user")
    a.set_password("x")
    b = User(username=f"d_{suffix}", email=f"b_{suffix}@e.com", role="user")
    b.set_password("x")
    db.session.add(a)
    db.session.commit()
    db.session.add(b)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_duplicate_email_raises(app, db):
    """Унікальність email."""
    suffix = uuid.uuid4().hex[:8]
    email = f"same_{suffix}@e.com"
    a = User(username=f"u1_{suffix}", email=email, role="user")
    b = User(username=f"u2_{suffix}", email=email, role="user")
    a.set_password("x")
    b.set_password("x")
    db.session.add(a)
    db.session.commit()
    db.session.add(b)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_duplicate_company_name_raises(app, db):
    """Унікальність назви компанії."""
    name = f"Co_{uuid.uuid4().hex[:8]}"[:100]
    a = Company(name=name)
    b = Company(name=name)
    db.session.add(a)
    db.session.commit()
    db.session.add(b)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


@pytest.mark.parametrize("verified", [True, False])
def test_company_is_verified_flag(app, db, verified):
    """Прапорець ``is_verified``."""
    name = f"V_{uuid.uuid4().hex[:10]}"[:100]
    c = Company(name=name, is_verified=verified)
    db.session.add(c)
    db.session.commit()
    assert Company.query.filter_by(name=name).first().is_verified is verified
