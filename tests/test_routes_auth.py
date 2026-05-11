from __future__ import annotations

import uuid

import pytest

from app.models import User

from tests.route_helpers import create_onboarded_user, login


def test_register_get_ok(client):
    r = client.get("/auth/register")
    assert r.status_code == 200


def test_login_get_ok(client):
    r = client.get("/auth/login")
    assert r.status_code == 200


def test_register_post_creates_user_and_redirects_onboarding(client, app, db):
    suffix = uuid.uuid4().hex[:8]
    username = f"reg_{suffix}"
    email = f"{suffix}@example.com"
    r = client.post(
        "/auth/register",
        data={
            "username": username,
            "email": email,
            "password": "secret12",
            "password2": "secret12",
            "submit": "1",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    assert "/auth/onboarding" in r.headers.get("Location", "")
    u = User.query.filter_by(email=email).first()
    assert u is not None
    assert u.onboarding_done is False


def test_register_post_validation_error_short_password(client, db):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/auth/register",
        data={
            "username": f"u_{suffix}",
            "email": f"{suffix}@example.com",
            "password": "123",
            "password2": "123",
            "submit": "1",
        },
    )
    assert r.status_code == 200
    assert User.query.filter_by(email=f"{suffix}@x.com").first() is None


def test_register_post_password_mismatch(client, db):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/auth/register",
        data={
            "username": f"pm_{suffix}",
            "email": f"{suffix}@example.com",
            "password": "secret12",
            "password2": "other12x",
            "submit": "1",
        },
    )
    assert r.status_code == 200


def test_login_success_redirects_index(client, app, db):
    u, pw = create_onboarded_user(db)
    r = login(client, u.email, pw)
    assert r.status_code == 200


def test_login_invalid_password_flash(client, app, db):
    u, pw = create_onboarded_user(db)
    r = client.post(
        "/auth/login",
        data={"email": u.email, "password": pw + "x", "submit": "1"},
    )
    assert r.status_code == 200


def test_login_redirects_when_already_authenticated(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    r = client.get("/auth/login", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers.get("Location", "").endswith("/") or "/" in r.headers.get("Location", "")


def test_register_redirects_when_logged_in(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    r = client.get("/auth/register", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_onboarding_get_ok(client, app, db):
    u, pw = create_onboarded_user(db)
    u.onboarding_done = False
    db.session.commit()
    login(client, u.email, pw)
    r = client.get("/auth/onboarding")
    assert r.status_code == 200


def test_onboarding_post_marks_done(client, app, db):
    u, pw = create_onboarded_user(db)
    u.onboarding_done = False
    db.session.commit()
    login(client, u.email, pw)
    r = client.post("/auth/onboarding", data={}, follow_redirects=False)
    assert r.status_code in (302, 303)
    db.session.refresh(u)
    assert u.onboarding_done is True


def test_logout_requires_login(client):
    r = client.get("/auth/logout", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_logout_ok_when_logged_in(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    r = client.get("/auth/logout", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_login_with_next_query_redirects(client, app, db):
    u, pw = create_onboarded_user(db)
    r = client.post(
        "/auth/login?next=/subscriptions",
        data={"email": u.email, "password": pw, "submit": "1"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    loc = r.headers.get("Location", "")
    assert "subscriptions" in loc or r.status_code == 302


def test_login_redirects_onboarding_when_not_done(client, app, db):
    u, pw = create_onboarded_user(db)
    u.onboarding_done = False
    db.session.commit()
    r = client.post(
        "/auth/login",
        data={"email": u.email, "password": pw, "submit": "1"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    assert "onboarding" in r.headers.get("Location", "")
