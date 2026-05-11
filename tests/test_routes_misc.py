"""Профіль, організації, обране, сповіщення, адмін — інтеграційні HTTP-тести."""

from __future__ import annotations

import json
import uuid

from app.models import Notification, OrganizationRequest

from tests.route_helpers import (
    create_admin_user,
    create_company,
    create_onboarded_user,
    create_pending_event,
    create_published_event,
    first_category_id,
    login,
)


def test_me_get_tabs(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    for tab in ("profile", "events", "org", "security"):
        r = client.get(f"/me?tab={tab}")
        assert r.status_code == 200


def test_me_invalid_tab_falls_back(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    r = client.get("/me?tab=not_a_real_tab")
    assert r.status_code == 200


def test_me_post_profile_update(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    r = client.post(
        "/me",
        data={
            "p-full_name": "Тест Імʼя",
            "p-headline": "Headline text",
            "p-bio": "Біографія користувача для тесту.",
            "p-education": "КПІ",
            "p-work": "Dev",
            "p-submit": "1",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)


def test_me_post_change_password_wrong_current(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    r = client.post(
        "/me?tab=security",
        data={
            "s-current_password": "wrong-password",
            "s-new_password": "newpass12",
            "s-new_password2": "newpass12",
            "s-submit": "1",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)


def test_me_post_change_password_success(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    r = client.post(
        "/me?tab=security",
        data={
            "s-current_password": pw,
            "s-new_password": "newpass99",
            "s-new_password2": "newpass99",
            "s-submit": "1",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    client.get("/auth/logout", follow_redirects=True)
    r2 = login(client, u.email, "newpass99")
    assert r2.status_code == 200


def test_user_profile_get_ok(client, app, db):
    u, _ = create_onboarded_user(db)
    r = client.get(f"/user/{u.username}")
    assert r.status_code == 200


def test_user_profile_404(client):
    r = client.get("/user/nonexistent_username_xyz_404")
    assert r.status_code == 404


def test_company_profile_get(client, app, db):
    c = create_company(db)
    r = client.get(f"/company/{c.id}")
    assert r.status_code == 200


def test_follow_user_post(client, app, db):
    target, _ = create_onboarded_user(db)
    follower, pw_f = create_onboarded_user(db)
    login(client, follower.email, pw_f)
    r = client.post(f"/user/{target.username}/follow", data={}, follow_redirects=False)
    assert r.status_code in (302, 303)


def test_follow_self_noop_redirect(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    r = client.post(f"/user/{u.username}/follow", data={}, follow_redirects=False)
    assert r.status_code in (302, 303)


def test_company_subscribe_profile_post(client, app, db):
    u, pw = create_onboarded_user(db)
    c = create_company(db)
    login(client, u.email, pw)
    r = client.post(f"/company/{c.id}/subscribe", data={}, follow_redirects=False)
    assert r.status_code in (302, 303)


def test_organization_request_get_and_post(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    g = client.get("/organizations/request")
    assert g.status_code == 200
    suffix = uuid.uuid4().hex[:6]
    r = client.post(
        "/organizations/request",
        data={
            "company_name": f"Нова орг {suffix}",
            "social_link": "https://example.com/org",
            "contact_email": f"org{suffix}@example.com",
            "comment": "Тестовий запит",
            "submit": "1",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    assert OrganizationRequest.query.filter_by(requester_id=u.id).count() >= 1


def test_organization_request_blocked_when_has_company(client, app, db):
    u, pw = create_onboarded_user(db)
    c = create_company(db)
    u.company_id = c.id
    db.session.commit()
    login(client, u.email, pw)
    r = client.get("/organizations/request", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_organization_request_blocked_when_pending_exists(client, app, db):
    u, pw = create_onboarded_user(db)
    db.session.add(
        OrganizationRequest(
            requester_id=u.id,
            company_name="Pending Org",
            contact_email="p@example.com",
            status="pending",
        )
    )
    db.session.commit()
    login(client, u.email, pw)
    r = client.get("/organizations/request", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_favorites_index_requires_login(client):
    r = client.get("/favorites/", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_favorites_index_and_toggle(client, app, db):
    author, _ = create_onboarded_user(db)
    e = create_published_event(db, author)
    fan, pw = create_onboarded_user(db)
    login(client, fan.email, pw)
    r0 = client.get("/favorites/")
    assert r0.status_code == 200
    r1 = client.post(
        f"/favorites/toggle/{e.id}",
        data={},
        headers={"Referer": "http://localhost/"},
        follow_redirects=False,
    )
    assert r1.status_code in (302, 303)
    r2 = client.post(
        f"/favorites/toggle/{e.id}",
        headers={"X-Requested-With": "XMLHttpRequest"},
        data={},
    )
    assert r2.status_code == 200
    data = json.loads(r2.data.decode())
    assert "is_favorite" in data


def test_notifications_index_and_read_all(client, app, db):
    u, pw = create_onboarded_user(db)
    db.session.add(
        Notification(
            user_id=u.id,
            type="test_route",
            title="T",
            message="Hello notification",
            is_read=False,
        )
    )
    db.session.commit()
    login(client, u.email, pw)
    r = client.get("/notifications/")
    assert r.status_code == 200
    r2 = client.get("/notifications/read-all", follow_redirects=False)
    assert r2.status_code in (302, 303)


def test_notifications_read_redirects_without_event(client, app, db):
    u, pw = create_onboarded_user(db)
    n = Notification(user_id=u.id, type="t2", title="T2", message="M2", event_id=None)
    db.session.add(n)
    db.session.commit()
    login(client, u.email, pw)
    r = client.get(f"/notifications/read/{n.id}", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_notifications_read_redirects_to_event(client, app, db):
    u, pw = create_onboarded_user(db)
    e = create_published_event(db, u)
    n = Notification(user_id=u.id, type="t3", title="T3", message="M3", event_id=e.id)
    db.session.add(n)
    db.session.commit()
    login(client, u.email, pw)
    r = client.get(f"/notifications/read/{n.id}", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert str(e.id) in r.headers.get("Location", "")


def test_notifications_create_post_forbidden_without_verified_company(client, app, db):
    u, pw = create_onboarded_user(db)
    co = create_company(db)
    u.company_id = co.id
    db.session.commit()
    login(client, u.email, pw)
    r = client.get("/notifications/posts/create", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_admin_dashboard_forbidden_for_user(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    r = client.get("/admin/", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_admin_dashboard_ok(client, app, db):
    adm, pw = create_admin_user(db)
    login(client, adm.email, pw)
    r = client.get("/admin/")
    assert r.status_code == 200


def test_admin_approve_event_get(client, app, db):
    adm, pwa = create_admin_user(db)
    author, _ = create_onboarded_user(db)
    pe = create_pending_event(db, author)
    login(client, adm.email, pwa)
    r = client.get(f"/admin/approve/{pe.id}", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_admin_reject_event_get(client, app, db):
    adm, pwa = create_admin_user(db)
    author, _ = create_onboarded_user(db)
    pe = create_pending_event(db, author, title="RejectThisOne")
    login(client, adm.email, pwa)
    r = client.get(f"/admin/reject/{pe.id}", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_admin_org_requests_list(client, app, db):
    adm, pwa = create_admin_user(db)
    login(client, adm.email, pwa)
    r = client.get("/admin/org-requests")
    assert r.status_code == 200
    r2 = client.get("/admin/org-requests?status=approved")
    assert r2.status_code == 200


def test_edit_event_get_author(client, app, db):
    u, pw = create_onboarded_user(db)
    e = create_pending_event(db, u)
    login(client, u.email, pw)
    r = client.get(f"/event/{e.id}/edit")
    assert r.status_code == 200


def test_add_event_post_with_optional_link(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    cid = first_category_id(db)
    r = client.post(
        "/add",
        data={
            "title": "Another Event With Link",
            "description": "Ще один довгий опис для події з посиланням.",
            "requirements": "reqs",
            "deadline": "",
            "link": "https://example.com/info",
            "format": "offline",
            "city": "Одеса",
            "category_id": str(cid),
            "company_id": "0",
            "submit": "1",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
