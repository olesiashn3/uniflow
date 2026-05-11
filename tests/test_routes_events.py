from __future__ import annotations

from app.models import Event, Question

from tests.route_helpers import (
    create_company,
    create_onboarded_user,
    create_pending_event,
    create_published_event,
    first_category_id,
    login,
)


def test_index_get_anonymous(client):
    r = client.get("/")
    assert r.status_code == 200


def test_index_get_with_query_params(client, app, db):
    author, _ = create_onboarded_user(db)
    create_published_event(db, author)
    r = client.get("/?sort=deadline&search=Integration&category=0&feed=all&format=online&city=Київ")
    assert r.status_code == 200


def test_index_feed_foryou_authenticated(client, app, db):
    u, pw = create_onboarded_user(db)
    create_published_event(db, u)
    login(client, u.email, pw)
    r = client.get("/?feed=foryou")
    assert r.status_code == 200


def test_index_feed_subscriptions(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    r = client.get("/?feed=subscriptions")
    assert r.status_code == 200


def test_event_detail_public_event(client, app, db):
    u, _ = create_onboarded_user(db)
    e = create_published_event(db, u)
    r = client.get(f"/event/{e.id}")
    assert r.status_code == 200


def test_event_detail_hidden_pending_for_anonymous(client, app, db):
    u, _ = create_onboarded_user(db)
    e = create_pending_event(db, u)
    r = client.get(f"/event/{e.id}", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_add_event_get_redirects_when_not_logged_in(client):
    r = client.get("/add", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_add_event_get_ok_when_logged_in(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    r = client.get("/add")
    assert r.status_code == 200


def test_add_event_post_creates_pending(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    cid = first_category_id(db)
    r = client.post(
        "/add",
        data={
            "title": "Route Created Event Title",
            "description": "Довгий опис події для успішної валідації форми.",
            "requirements": "",
            "deadline": "",
            "link": "",
            "format": "online",
            "city": "Львів",
            "category_id": str(cid),
            "company_id": "0",
            "submit": "1",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    ev = Event.query.filter(Event.title == "Route Created Event Title").first()
    assert ev is not None
    assert ev.status == "pending"


def test_my_events_redirects_to_profile(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    r = client.get("/my-events", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "me" in r.headers.get("Location", "")


def test_subscriptions_get_requires_login(client):
    r = client.get("/subscriptions", follow_redirects=False)
    assert r.status_code in (302, 303)


def test_subscriptions_get_ok(client, app, db):
    u, pw = create_onboarded_user(db)
    login(client, u.email, pw)
    r = client.get("/subscriptions")
    assert r.status_code == 200


def test_toggle_subscribe_post(client, app, db):
    u, pw = create_onboarded_user(db)
    co = create_company(db)
    login(client, u.email, pw)
    r = client.post(
        f"/company/{co.id}/toggle_subscribe",
        data={},
        follow_redirects=False,
        headers={"Referer": "http://localhost/"},
    )
    assert r.status_code in (302, 303)


def test_ask_question_post_empty(client, app, db):
    u, pw = create_onboarded_user(db)
    e = create_published_event(db, u)
    login(client, u.email, pw)
    r = client.post(f"/event/{e.id}/ask", data={"question": "   "}, follow_redirects=False)
    assert r.status_code in (302, 303)


def test_ask_question_post_ok(client, app, db):
    author, pw_a = create_onboarded_user(db)
    e = create_published_event(db, author)
    asker, pw_b = create_onboarded_user(db)
    login(client, asker.email, pw_b)
    r = client.post(
        f"/event/{e.id}/ask",
        data={"question": "Чи можна взяти участь дистанційно?"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    assert Question.query.filter_by(event_id=e.id).count() >= 1


def test_answer_question_post_as_author(client, app, db):
    author, pw_a = create_onboarded_user(db)
    e = create_published_event(db, author)
    asker, pw_b = create_onboarded_user(db)
    q = Question(text="Q text here", user_id=asker.id, event_id=e.id)
    db.session.add(q)
    db.session.commit()

    login(client, author.email, pw_a)
    r = client.post(
        f"/question/{q.id}/answer",
        data={"answer": "Так, можна дистанційно."},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    db.session.refresh(q)
    assert q.answer is not None


def test_answer_question_forbidden_for_non_author(client, app, db):
    author, pw_a = create_onboarded_user(db)
    other, pw_o = create_onboarded_user(db)
    e = create_published_event(db, author)
    asker, _ = create_onboarded_user(db)
    q = Question(text="Q2", user_id=asker.id, event_id=e.id)
    db.session.add(q)
    db.session.commit()

    login(client, other.email, pw_o)
    r = client.post(
        f"/question/{q.id}/answer",
        data={"answer": "Hacked"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)


def test_answer_question_empty_body(client, app, db):
    author, pw_a = create_onboarded_user(db)
    e = create_published_event(db, author)
    asker, _ = create_onboarded_user(db)
    q = Question(text="Q3", user_id=asker.id, event_id=e.id)
    db.session.add(q)
    db.session.commit()
    login(client, author.email, pw_a)
    r = client.post(f"/question/{q.id}/answer", data={"answer": "  "})
    assert r.status_code in (302, 303)


def test_delete_event_post_forbidden_non_owner(client, app, db):
    owner, pw_o = create_onboarded_user(db)
    intruder, pw_i = create_onboarded_user(db)
    e = create_pending_event(db, owner)
    login(client, intruder.email, pw_i)
    r = client.post(f"/event/{e.id}/delete", data={}, follow_redirects=False)
    assert r.status_code in (302, 303)


def test_delete_event_post_owner(client, app, db):
    owner, pw_o = create_onboarded_user(db)
    e = create_pending_event(db, owner, title="ToDeleteEventTitleX")
    login(client, owner.email, pw_o)
    r = client.post(f"/event/{e.id}/delete", data={}, follow_redirects=False)
    assert r.status_code in (302, 303)
    assert db.session.get(Event, e.id) is None
