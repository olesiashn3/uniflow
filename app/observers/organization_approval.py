from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class OrganizationApprovedContext:
    """Payload when an organization request is approved."""

    requester_id: int
    company_name: str


class OrganizationApprovalObserver(ABC):
    """Observer interface for organization-request approval."""

    @abstractmethod
    def on_organization_request_approved(self, ctx: OrganizationApprovedContext) -> None:
        """Handle an approved organization request."""


class OrganizationApprovalSubject:
    """Notifies registered observers."""

    def __init__(self) -> None:
        self._observers: List[OrganizationApprovalObserver] = []

    def attach(self, observer: OrganizationApprovalObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: OrganizationApprovalObserver) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, ctx: OrganizationApprovedContext) -> None:
        for observer in list(self._observers):
            observer.on_organization_request_approved(ctx)


class OrganizationApprovedNotificationObserver(OrganizationApprovalObserver):
    """Creates an in-app notification for the requester."""

    def on_organization_request_approved(self, ctx: OrganizationApprovedContext) -> None:
        from app.services.notifications_service import (
            create_organization_request_approved_notification,
        )

        create_organization_request_approved_notification(
            user_id=ctx.requester_id,
            company_name=ctx.company_name,
        )


_subject: Optional[OrganizationApprovalSubject] = None


def get_organization_approval_subject() -> OrganizationApprovalSubject:
    """Return the process-wide subject instance (lazy init with default observers)."""
    global _subject
    if _subject is None:
        _subject = OrganizationApprovalSubject()
        _subject.attach(OrganizationApprovedNotificationObserver())
    return _subject


def notify_organization_request_approved(*, requester_id: int, company_name: str) -> None:
    """Notify observers after a successful organization approval commit."""
    ctx = OrganizationApprovedContext(requester_id=requester_id, company_name=company_name)
    get_organization_approval_subject().notify(ctx)
