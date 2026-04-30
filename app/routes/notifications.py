import os
import secrets

from PIL import Image
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user

from app.forms import NewsPostForm
from app.models import Notification
from app.services.notifications_service import (
    get_user_notifications,
    generate_deadline_reminders_for_user,
    mark_notification_as_read,
    mark_all_notifications_as_read
)
from app.services.news_service import (
    get_news_for_user_subscriptions,
    get_company_news,
    create_news_post
)

notifications = Blueprint('notifications', __name__)


def save_news_image(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/uploads', picture_fn)

    output_size = (1200, 630)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@notifications.route('/')
@login_required
def index():
    generate_deadline_reminders_for_user(current_user)
    items = get_user_notifications(current_user.id)

    news_posts = get_news_for_user_subscriptions(current_user, limit=6)

    org_posts = []
    can_post_as_org = bool(current_user.company and current_user.company.is_verified)
    if can_post_as_org:
        org_posts = get_company_news(current_user.company.id, limit=4)

    return render_template(
        'notifications/index.html',
        notifications=items,
        news_posts=news_posts,
        can_post_as_org=can_post_as_org,
        org_posts=org_posts,
    )


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


@notifications.route('/posts/create', methods=['GET', 'POST'])
@login_required
def create_post():
    if not current_user.company or not current_user.company.is_verified:
        flash('Створювати дописи можуть лише верифіковані організації.', 'danger')
        return redirect(url_for('notifications.index'))

    form = NewsPostForm()
    if form.validate_on_submit():
        picture_file = None
        if form.image.data:
            picture_file = save_news_image(form.image.data)

        create_news_post(
            company=current_user.company,
            title=form.title.data,
            body=form.body.data,
            image_file=picture_file,
        )
        flash('Допис опубліковано!', 'success')
        return redirect(url_for('notifications.index'))

    return render_template('notifications/create_post.html', form=form)

