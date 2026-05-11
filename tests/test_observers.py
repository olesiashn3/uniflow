from __future__ import annotations

import uuid
from typing import List

import pytest

from app.observers.organization_approval import (
    OrganizationApprovalObserver,
    OrganizationApprovalSubject,
    OrganizationApprovedContext,
    OrganizationApprovedNotificationObserver,
    get_organization_approval_subject,
    notify_organization_request_approved,
)
from app.models import Notification


class _RecordingObserver(OrganizationApprovalObserver):
    def __init__(self) -> None:
        self.calls: List[OrganizationApprovedContext] = []

    def on_organization_request_approved(self, ctx: OrganizationApprovedContext) -> None:
        self.calls.append(ctx)


pytestmark = pytest.mark.usefixtures("reset_organization_approval_subject")


def test_subject_attach_notify_single():
    """Single observer receives one notification call."""
    subject = OrganizationApprovalSubject()
    rec = _RecordingObserver()
    subject.attach(rec)
    ctx = OrganizationApprovedContext(requester_id=7, company_name="Lab")
    subject.notify(ctx)
    assert len(rec.calls) == 1
    assert rec.calls[0].requester_id == 7
    assert rec.calls[0].company_name == "Lab"


@pytest.mark.parametrize("uid", range(1, 31))
def test_subject_multicast_three_observers(uid):
    """Multiple observers each receive the same event."""
    subject = OrganizationApprovalSubject()
    observers = [_RecordingObserver() for _ in range(3)]
    for o in observers:
        subject.attach(o)
    subject.notify(OrganizationApprovedContext(requester_id=uid, company_name=f"Org{uid}"))
    for o in observers:
        assert len(o.calls) == 1
        assert o.calls[0].requester_id == uid


@pytest.mark.parametrize("n", range(20))
def test_detach_stops_delivery(n):
    """Detached observer is not invoked."""
    subject = OrganizationApprovalSubject()
    rec = _RecordingObserver()
    subject.attach(rec)
    subject.detach(rec)
    subject.notify(OrganizationApprovedContext(1, "X"))
    assert rec.calls == []


@pytest.mark.parametrize("n", range(15))
def test_attach_idempotent(n):
    """Duplicate attach registers the observer once."""
    subject = OrganizationApprovalSubject()
    rec = _RecordingObserver()
    subject.attach(rec)
    subject.attach(rec)
    subject.notify(OrganizationApprovedContext(2, "Y"))
    assert len(rec.calls) == 1


def test_context_is_frozen():
    """OrganizationApprovedContext is a frozen dataclass."""
    import dataclasses

    ctx = OrganizationApprovedContext(requester_id=3, company_name="Z")
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        ctx.requester_id = 99  # type: ignore[misc]


@pytest.mark.parametrize("name", ["A", "Довга назва компанії " * 3, "Co <>&"])
def test_notify_integration_creates_notification(app, db, user, name):
    """notify_organization_request_approved persists a Notification row."""
    import app.observers.organization_approval as org_mod

    org_mod._subject = None
    notify_organization_request_approved(requester_id=user.id, company_name=name)
    rows = Notification.query.filter_by(user_id=user.id).all()
    assert len(rows) >= 1
    assert any(name in r.message or name in r.title for r in rows)


@pytest.mark.parametrize("suffix", range(25))
def test_get_singleton_returns_same_instance(app, db, suffix):
    """get_organization_approval_subject returns the same instance."""
    del suffix
    a = get_organization_approval_subject()
    b = get_organization_approval_subject()
    assert a is b


def test_default_observer_type_on_fresh_singleton(app, db):
    """Fresh subject includes at least one default notification observer."""
    import app.observers.organization_approval as org_mod

    org_mod._subject = None
    subj = get_organization_approval_subject()
    assert len(subj._observers) >= 1
    assert any(isinstance(o, OrganizationApprovedNotificationObserver) for o in subj._observers)


@pytest.mark.parametrize("rid", [1, 42, 10**6])
def test_recording_observer_with_custom_subject(rid):
    """Local subject instance isolates observer tests from the singleton."""
    subject = OrganizationApprovalSubject()
    rec = _RecordingObserver()
    subject.attach(rec)
    subject.notify(OrganizationApprovedContext(requester_id=rid, company_name=str(uuid.uuid4())[:8]))
    assert rec.calls[0].requester_id == rid
