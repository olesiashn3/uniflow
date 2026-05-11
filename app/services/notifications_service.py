from datetime import date, timedelta

from app import db
from app.models import Notification, Event, Favorite


def get_unread_notifications_count(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def get_user_notifications(user_id):
    return Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).all()


def create_notification(user_id, notification_type, title, message, event_id=None):
    exists = Notification.query.filter_by(
        user_id=user_id,
        type=notification_type,
        event_id=event_id,
        title=title
    ).first()
    if exists:
        return exists

    notification = Notification(
        user_id=user_id,
        event_id=event_id,
        type=notification_type,
        title=title,
        message=message
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def create_approval_notification(event):
    return create_notification(
        user_id=event.author_id,
        notification_type='event_approved',
        title='Подію підтверджено',
        message=f'Твою подію "{event.title}" схвалено модератором. Вона вже доступна в стрічці.',
        event_id=event.id
    )


def create_rejection_notification(event):
    return create_notification(
        user_id=event.author_id,
        notification_type='event_rejected',
        title='Подію відхилено',
        message=f'Твою подію "{event.title}" відхилено модератором. Перевір опис і спробуй подати знову.',
        event_id=event.id
    )


def create_organization_request_approved_notification(user_id: int, company_name: str) -> Notification:
    """Persist a notification when an organization request is approved."""
    return create_notification(
        user_id=user_id,
        notification_type='organization_request_approved',
        title=f'Організацію «{company_name}» схвалено',
        message=(
            f'Ваш запит схвалено. Організацію «{company_name}» створено '
            f'та привʼязано до вашого профілю.'
        ),
        event_id=None,
    )


def generate_deadline_reminders_for_user(user):
    reminder_day = date.today() + timedelta(days=3)
    favorite_events = db.session.query(Event).join(
        Favorite, Favorite.event_id == Event.id
    ).filter(
        Favorite.user_id == user.id,
        Event.status == 'approved',
        Event.deadline == reminder_day
    ).all()

    for event in favorite_events:
        create_notification(
            user_id=user.id,
            notification_type='favorite_deadline_reminder_3d',
            title='Нагадування про дедлайн',
            message=f'До дедлайну збереженої події "{event.title}" залишилося 3 дні.',
            event_id=event.id
        )


def mark_notification_as_read(notification):
    notification.is_read = True
    db.session.commit()


def mark_all_notifications_as_read(user_id):
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()

