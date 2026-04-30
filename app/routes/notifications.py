from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from app.models import Notification
from app.services.notifications_service import (
    get_user_notifications,
    generate_deadline_reminders_for_user,
    mark_notification_as_read,
    mark_all_notifications_as_read
)

notifications = Blueprint('notifications', __name__)


@notifications.route('/')
@login_required
def index():
    generate_deadline_reminders_for_user(current_user)
    items = get_user_notifications(current_user.id)
    return render_template('notifications/index.html', notifications=items)


@notifications.route('/read/<int:notification_id>')
@login_required
def read(notification_id):
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=current_user.id
    ).first_or_404()
    if not notification.is_read:
        mark_notification_as_read(notification)

    if notification.event_id:
        return redirect(url_for('events.detail', id=notification.event_id))
    return redirect(url_for('notifications.index'))


@notifications.route('/read-all')
@login_required
def read_all():
    mark_all_notifications_as_read(current_user.id)
    return redirect(url_for('notifications.index'))

