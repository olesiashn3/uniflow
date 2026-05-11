"""
Патерн Observer: реакція на схвалення адміністратором запиту на створення організації.

Після успішного збереження стану в БД викликається ``notify_organization_request_approved``;
підписники (наприклад, створення ``Notification``) виконуються окремо від маршруту.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class OrganizationApprovedContext:
    """Контекст доменної події: запит на організацію схвалено."""

    requester_id: int
    company_name: str


class OrganizationApprovalObserver(ABC):
    """Спостерігач за схваленням запиту на організацію."""

    @abstractmethod
    def on_organization_request_approved(self, ctx: OrganizationApprovedContext) -> None:
        """Викликається після успішного схвалення запиту."""


class OrganizationApprovalSubject:
    """Суб'єкт: тримає список спостерігачів і розсилає їм подію."""

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
    """Створює in-app сповіщення для користувача, який подав запит."""

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
    """Повертає синглтон суб'єкта з дефолтним підписником на сповіщення."""
    global _subject
    if _subject is None:
        _subject = OrganizationApprovalSubject()
        _subject.attach(OrganizationApprovedNotificationObserver())
    return _subject


def notify_organization_request_approved(*, requester_id: int, company_name: str) -> None:
    """Точка входу для маршрутів після commit: сповістити всіх спостерігачів."""
    ctx = OrganizationApprovedContext(requester_id=requester_id, company_name=company_name)
    get_organization_approval_subject().notify(ctx)
