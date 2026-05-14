"""Targeted tests for coverage gaps (Sonar / pytest-cov)."""
from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app import db
from app.forms import RegisterForm
from app.models import (
    Category,
    Company,
    EventEditRequest,
    Favorite,
    OrganizationRequest,
    User,
    load_user,
)
from wtforms.validators import ValidationError
from app.repositories.event_repository import ListPagination, SqlAlchemyEventRepository
from app.services import admin_service
from app.services.auth_service import complete_onboarding
from app.services.events_service import build_events_query, is_event_visible_for_user
from app.services.news_service import get_news_for_user_subscriptions
from app.services.notifications_service import create_notification

from tests.helpers import DummyUserSubscriptions, make_event_stub
from tests.route_helpers import (
    create_admin_user,
    create_company,
    create_onboarded_user,
    create_pending_event,
    create_published_event,
    first_category_id,
    login,
)


def test_list_pagination_edge_properties():
    """Exercise ListPagination branches not hit via InMemoryPublicEventsResult alone."""
    p0 = ListPagination([], page=1, per_page=0, total=10)
    assert p0.pages == 0
    assert p0.has_next is False
    assert p0.has_prev is False
    assert p0.prev_num is None
    assert p0.next_num is None

    p_empty = ListPagination([], page=1, per_page=9, total=0)
    assert p_empty.pages == 1

    p_mid = ListPagination([1, 2], page=2, per_page=2, total=5)
    assert p_mid.has_prev is True
    assert p_mid.has_next is True
    assert p_mid.prev_num == 1
    assert p_mid.next_num == 3

    p_last = ListPagination([9], page=3, per_page=2, total=5)
    assert p_last.has_next is False
    assert p_last.next_num is None


def test_in_memory_subscriptions_excludes_non_matching_events():
    """_match_subscription returns False when event matches neither company nor author."""
    today = date.today()
    c = type("C", (), {"id": 1})()
    u = type("U", (), {"id": 99})()
    user = DummyUserSubscriptions([c], [u])
    ev = make_event_stub(
        company_id=2,
        author_id=3,
        deadline=today + timedelta(days=1),
        status="approved",
    )
    from app.repositories.event_repository import InMemoryEventRepository

    repo = InMemoryEventRepository([ev])
    p = repo.build_public_events_query(feed="subscriptions", user=user).paginate(1, 9)
    assert p.total == 0


def test_in_memory_subscriptions_or_filter_both_company_and_author():
    """subscriptions feed uses OR when both subscription sources exist."""
    today = date.today()
    c = type("C", (), {"id": 7})()
    author_u = type("U", (), {"id": 50})()
    user = DummyUserSubscriptions([c], [author_u])
    ev_company = make_event_stub(
        eid=1,
        company_id=7,
        author_id=1,
        deadline=today + timedelta(days=1),
        status="approved",
    )
    ev_author = make_event_stub(
        eid=2,
        company_id=None,
        author_id=50,
        deadline=today + timedelta(days=1),
        status="approved",
    )
    from app.repositories.event_repository import InMemoryEventRepository

    repo = InMemoryEventRepository([ev_company, ev_author])
    p = repo.build_public_events_query(feed="subscriptions", user=user).paginate(1, 9)
    assert p.total == 2


def test_sqlalchemy_repo_foryou_filters_by_interests(app, db):
    """SqlAlchemy foryou branch with non-empty recommended_category_ids."""
    u, pw = create_onboarded_user(db)
    cat = Category.query.order_by(Category.id).first()
    u.interests.append(cat)
    db.session.commit()
    author, _ = create_onboarded_user(db)
    create_published_event(db, author, category_id=cat.id)
    repo = SqlAlchemyEventRepository()
    q = repo.build_public_events_query(feed="foryou", user=u)
    assert q.count() >= 1


def test_sqlalchemy_repo_subscriptions_company_and_category_filter(app, db):
    """SqlAlchemy subscriptions feed with company subscription."""
    fan, pw = create_onboarded_user(db)
    author, _ = create_onboarded_user(db)
    co = create_company(db)
    fan.subscribed_companies.append(co)
    db.session.commit()
    create_published_event(db, author, company_id=co.id)
    repo = SqlAlchemyEventRepository()
    q = repo.build_public_events_query(feed="subscriptions", user=fan)
    assert q.count() >= 1


def test_sqlalchemy_repo_subscriptions_followed_author(app, db):
    """SqlAlchemy subscriptions feed with followed author only."""
    fan, pw_f = create_onboarded_user(db)
    author, _ = create_onboarded_user(db)
    fan.follow(author)
    db.session.commit()
    create_published_event(db, author, company_id=None)
    repo = SqlAlchemyEventRepository()
    q = repo.build_public_events_query(feed="subscriptions", user=fan)
    assert q.count() >= 1


def test_sqlalchemy_repo_category_and_search_filters(app, db):
    """category_id > 0, search, format_type, city_filter on SQLAlchemy repo."""
    author, _ = create_onboarded_user(db)
    cid = first_category_id(db)
    create_published_event(
        db,
        author,
        title="UniqueSearchTitleXyz",
        category_id=cid,
        format="online",
        city="Київ",
    )
    repo = SqlAlchemyEventRepository()
    q = repo.build_public_events_query(
        search="UniqueSearchTitleXyz",
        category_id=cid,
        format_type="online",
        city_filter="Киї",
    )
    assert q.count() >= 1


def test_build_events_query_passes_repository(app, db):
    """Optional repository parameter is honored."""
    from app.repositories.event_repository import InMemoryEventRepository

    today = date.today()
    ev = make_event_stub(deadline=today + timedelta(days=1), status="approved")
    repo = InMemoryEventRepository([ev])
    q = build_events_query(repository=repo)
    assert q.paginate(1, 9).total == 1


def test_load_user_returns_user(app, db):
    u, _ = create_onboarded_user(db)
    loaded = load_user(str(u.id))
    assert loaded is not None
    assert loaded.id == u.id


def test_user_is_following_none_is_false(app, db):
    u, _ = create_onboarded_user(db)
    assert u.is_following(None) is False


def test_user_follow_idempotent_and_unfollow(app, db):
    a, _ = create_onboarded_user(db)
    b, _ = create_onboarded_user(db)
    a.follow(b)
    a.follow(b)
    db.session.commit()
    assert a.is_following(b)
    a.unfollow(b)
    db.session.commit()
    assert not a.is_following(b)
    a.unfollow(b)
    db.session.commit()


def test_model_repr_smoke(app, db):
    c = create_company(db, name=f"ReprCo_{uuid.uuid4().hex[:8]}")
    cat = Category.query.first()
    u, _ = create_onboarded_user(db)
    e = create_pending_event(db, u)
    assert "Company" in repr(c)
    assert "Category" in repr(cat)
    assert "Event" in repr(e)


def test_register_form_duplicate_validators(app, db):
    u, _ = create_onboarded_user(db)
    with app.test_request_context():
        form = RegisterForm()
        form.username.data = u.username
        form.email.data = "other@example.com"
        with pytest.raises(ValidationError):
            form.validate_username(form.username)

        form2 = RegisterForm()
        form2.username.data = "newuser_unique"
        form2.email.data = u.email
        with pytest.raises(ValidationError):
            form2.validate_email(form2.email)


def test_news_service_unauthenticated_returns_empty():
    assert get_news_for_user_subscriptions(None) == []


def test_complete_onboarding_with_categories(app, db):
    u, _ = create_onboarded_user(db)
    cats = Category.query.limit(2).all()
    complete_onboarding(u, [c.id for c in cats])
    db.session.refresh(u)
    assert u.onboarding_done is True
    assert len(u.interests) >= 1


def test_create_notification_duplicate_returns_existing(app, db):
    u, _ = create_onboarded_user(db)
    n1 = create_notification(
        u.id,
        "dup_type",
        "DupTitle",
        "msg",
        event_id=None,
    )
    n2 = create_notification(
        u.id,
        "dup_type",
        "DupTitle",
        "msg",
        event_id=None,
    )
    assert n1.id == n2.id


def test_is_event_visible_pending_for_author_and_admin(app, db):
    author, _ = create_onboarded_user(db)
    admin_u, _ = create_admin_user(db)
    e = create_pending_event(db, author)
    anon = type("A", (), {"is_authenticated": False})()
    assert is_event_visible_for_user(e, anon) is False
    assert is_event_visible_for_user(e, author) is True
    assert is_event_visible_for_user(e, admin_u) is True


def test_admin_get_dashboard_data(app, db):
    author, _ = create_onboarded_user(db)
    create_pending_event(db, author, created_at=datetime.utcnow() - timedelta(days=10))
    create_published_event(db, author)
    admin_service.get_dashboard_data()


def test_admin_service_event_edit_and_assign_edges(app, db):
    adm, _ = create_admin_user(db)
    author, _ = create_onboarded_user(db)
    e = create_published_event(db, author)
    cid = first_category_id(db)
    req = EventEditRequest(
        event_id=e.id,
        requester_id=author.id,
        status="pending",
        title="New T",
        description="New description long enough for tests here.",
        requirements="r",
        deadline=date.today() + timedelta(days=5),
        link="https://example.com",
        format="online",
        city="Львів",
        image_file=None,
        category_id=cid,
        company_id=None,
    )
    db.session.add(req)
    db.session.commit()
    admin_service.approve_event_edit_request(req, adm)
    db.session.refresh(e)
    assert e.title == "New T"

    req2 = EventEditRequest(
        event_id=e.id,
        requester_id=author.id,
        status="pending",
        title=None,
        description=None,
        requirements=None,
        deadline=None,
        link=None,
        format=None,
        city=None,
        image_file=None,
        category_id=cid,
        company_id=None,
    )
    db.session.add(req2)
    db.session.commit()
    admin_service.reject_event_edit_request(req2, adm, admin_note="  nope  ")
    db.session.refresh(req2)
    assert req2.status == "rejected"
    assert req2.admin_note == "nope"

    req_missing = EventEditRequest(
        event_id=e.id,
        requester_id=author.id,
        status="pending",
        title="Ghost",
        description="Description long enough for ghost edit request.",
        requirements="",
        deadline=None,
        link=None,
        format=None,
        city=None,
        image_file=None,
        category_id=cid,
        company_id=None,
    )
    db.session.add(req_missing)
    db.session.commit()
    with patch("app.services.admin_service.Event") as EvMock:
        EvMock.query.get.return_value = None
        assert admin_service.approve_event_edit_request(req_missing, adm) is None

    u_none, c_none = admin_service.assign_user_to_company("no_such_user_ever", 1)
    assert u_none is None and c_none is None

    co = create_company(db)
    u2, co2 = admin_service.assign_user_to_company(author.username, co.id)
    assert u2.company_id == co2.id


def test_admin_routes_extended(client, app, db, reset_organization_approval_subject):
    adm, pwa = create_admin_user(db)
    author, _ = create_onboarded_user(db)
    pe = create_pending_event(db, author)
    co = create_company(db)
    login(client, adm.email, pwa)

    r = client.get("/admin/org-requests?status=invalid_status_xyz")
    assert r.status_code == 200

    req = OrganizationRequest(
        requester_id=author.id,
        company_name=f"OrgReq {uuid.uuid4().hex[:6]}",
        contact_email="contact@example.com",
        status="pending",
        social_link="https://example.com/org",
    )
    db.session.add(req)
    db.session.commit()

    r_ap = client.post(
        f"/admin/org-requests/{req.id}/approve",
        data={},
        follow_redirects=False,
    )
    assert r_ap.status_code in (302, 303)
    db.session.refresh(author)
    assert author.company_id is not None

    req2 = OrganizationRequest(
        requester_id=author.id,
        company_name="Second",
        contact_email="c2@example.com",
        status="pending",
    )
    db.session.add(req2)
    db.session.commit()
    r_rj = client.post(
        f"/admin/org-requests/{req2.id}/reject",
        data={"admin_note": "not suitable"},
        follow_redirects=False,
    )
    assert r_rj.status_code in (302, 303)

    fake_img = MagicMock()
    fake_img.thumbnail = MagicMock()
    fake_img.save = MagicMock()
    with patch("app.routes.admin.Image.open", return_value=fake_img):
        logo = (io.BytesIO(b"fake"), "logo.png")
        r_cc = client.post(
            "/admin/companies/create",
            data={
                "name": f"AdminCo {uuid.uuid4().hex[:6]}",
                "description": "d",
                "website": "https://example.com",
                "logo": logo,
                "submit": "1",
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
    assert r_cc.status_code in (302, 303)

    r_v = client.get(f"/admin/companies/verify/{co.id}", follow_redirects=False)
    assert r_v.status_code in (302, 303)
    r_v2 = client.get(f"/admin/companies/verify/{co.id}", follow_redirects=False)
    assert r_v2.status_code in (302, 303)

    r_as = client.post(
        "/admin/companies/assign",
        data={
            "username": "nope_user_missing",
            "company_id": str(co.id),
            "submit": "1",
        },
        follow_redirects=False,
    )
    assert r_as.status_code in (302, 303)

    r_as_ok = client.post(
        "/admin/companies/assign",
        data={
            "username": author.username,
            "company_id": str(co.id),
            "submit": "1",
        },
        follow_redirects=False,
    )
    assert r_as_ok.status_code in (302, 303)

    er = EventEditRequest(
        event_id=pe.id,
        requester_id=author.id,
        status="pending",
        title="Edited",
        description="Long enough description for edit request body text.",
        requirements="",
        deadline=date.today() + timedelta(days=10),
        link=None,
        format="online",
        city="Київ",
        image_file=None,
        category_id=first_category_id(db),
        company_id=None,
    )
    db.session.add(er)
    db.session.commit()

    r_ea = client.post(
        f"/admin/event-edits/{er.id}/approve",
        data={},
        follow_redirects=False,
    )
    assert r_ea.status_code in (302, 303)

    er2 = EventEditRequest(
        event_id=pe.id,
        requester_id=author.id,
        status="pending",
        title="E2",
        description="Another long description for pending edit request.",
        requirements="",
        deadline=date.today() + timedelta(days=11),
        link=None,
        format="offline",
        city=None,
        image_file=None,
        category_id=first_category_id(db),
        company_id=None,
    )
    db.session.add(er2)
    db.session.commit()
    er2.status = "approved"
    db.session.commit()
    r_dup = client.post(
        f"/admin/event-edits/{er2.id}/approve",
        data={},
        follow_redirects=False,
    )
    assert r_dup.status_code in (302, 303)

    er_none = EventEditRequest(
        event_id=pe.id,
        requester_id=author.id,
        status="pending",
        title="NonePath",
        description="Description long enough for the pending edit request branch.",
        requirements="",
        deadline=date.today() + timedelta(days=9),
        link=None,
        format=None,
        city=None,
        image_file=None,
        category_id=first_category_id(db),
        company_id=None,
    )
    db.session.add(er_none)
    db.session.commit()
    with patch("app.routes.admin.approve_event_edit_request", return_value=None):
        r_bad = client.post(
            f"/admin/event-edits/{er_none.id}/approve",
            data={},
            follow_redirects=False,
        )
    assert r_bad.status_code in (302, 303)

    er3 = EventEditRequest(
        event_id=pe.id,
        requester_id=author.id,
        status="pending",
        title="RejectMe",
        description="Description long enough for validation rules in tests.",
        requirements="",
        deadline=date.today() + timedelta(days=12),
        link=None,
        format=None,
        city=None,
        image_file=None,
        category_id=first_category_id(db),
        company_id=None,
    )
    db.session.add(er3)
    db.session.commit()
    r_erj = client.post(
        f"/admin/event-edits/{er3.id}/reject",
        data={"admin_note": "  note  "},
        follow_redirects=False,
    )
    assert r_erj.status_code in (302, 303)


def test_event_detail_calendar_with_link(client, app, db):
    u, _ = create_onboarded_user(db)
    e = create_published_event(db, u, link="https://example.com/event")
    r = client.get(f"/event/{e.id}")
    assert r.status_code == 200


def test_event_edit_post_creates_edit_request(client, app, db):
    u, pw = create_onboarded_user(db)
    e = create_published_event(db, u)
    login(client, u.email, pw)
    cid = first_category_id(db)
    r = client.post(
        f"/event/{e.id}/edit",
        data={
            "title": "Updated Event Title Here",
            "description": "Updated long description for the event edit form submit.",
            "requirements": "",
            "deadline": "",
            "link": "https://example.com/details",
            "format": "online",
            "city": "Одеса",
            "category_id": str(cid),
            "company_id": "0",
            "submit": "1",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    assert EventEditRequest.query.filter_by(event_id=e.id).count() >= 1


def test_toggle_subscribe_unsubscribe_flash(client, app, db):
    u, pw = create_onboarded_user(db)
    co = create_company(db)
    login(client, u.email, pw)
    client.post(
        f"/company/{co.id}/toggle_subscribe",
        data={},
        headers={"Referer": "http://localhost/"},
        follow_redirects=False,
    )
    r2 = client.post(
        f"/company/{co.id}/toggle_subscribe",
        data={},
        headers={"Referer": "http://localhost/"},
        follow_redirects=False,
    )
    assert r2.status_code in (302, 303)


def test_add_event_with_image_mock(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    cid = first_category_id(db)
    fake_img = MagicMock()
    fake_img.thumbnail = MagicMock()
    fake_img.save = MagicMock()
    img = (io.BytesIO(b"x"), "banner.jpg")
    with patch("app.routes.events.Image.open", return_value=fake_img):
        r = client.post(
            "/add",
            data={
                "title": "Event With Banner Image",
                "description": "Description long enough for the event creation form validation.",
                "requirements": "",
                "deadline": "",
                "link": "",
                "format": "online",
                "city": "Львів",
                "category_id": str(cid),
                "company_id": "0",
                "image": img,
                "submit": "1",
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
    assert r.status_code in (302, 303)


def test_notifications_create_post_with_image(client, app, db):
    u, pw = create_onboarded_user(db)
    co = create_company(db)
    co.is_verified = True
    u.company_id = co.id
    db.session.commit()
    login(client, u.email, pw)
    fake_img = MagicMock()
    fake_img.thumbnail = MagicMock()
    fake_img.save = MagicMock()
    img = (io.BytesIO(b"x"), "news.jpg")
    with patch("app.routes.notifications.Image.open", return_value=fake_img):
        r = client.post(
            "/notifications/posts/create",
            data={
                "title": "News headline here",
                "body": "News body text long enough for validation rules in the form.",
                "image": img,
                "submit": "1",
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
    assert r.status_code in (302, 303)


def test_profile_me_avatar_upload(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    fake_img = MagicMock()
    fake_img.thumbnail = MagicMock()
    fake_img.save = MagicMock()
    av = (io.BytesIO(b"x"), "av.png")
    with patch("app.routes.profile.Image.open", return_value=fake_img):
        r = client.post(
            "/me",
            data={
                "p-full_name": "Name",
                "p-headline": "H",
                "p-bio": "Bio text for profile.",
                "p-education": "E",
                "p-work": "W",
                "p-avatar": av,
                "p-submit": "1",
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
    assert r.status_code in (302, 303)


def test_notifications_deadline_reminder_branch(client, app, db):
    """Opening notifications index runs generate_deadline_reminders_for_user."""
    fan, pw = create_onboarded_user(db)
    author, _ = create_onboarded_user(db)
    e = create_published_event(db, author, deadline=date.today() + timedelta(days=3))
    db.session.add(Favorite(user_id=fan.id, event_id=e.id))
    db.session.commit()
    login(client, fan.email, pw)
    r = client.get("/notifications/")
    assert r.status_code == 200


def test_context_processor_unread_badge_logged_in(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    r = client.get("/")
    assert r.status_code == 200
