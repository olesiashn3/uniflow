import os
import secrets

from PIL import Image
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models import User, Company, UserProfile, OrganizationRequest
from datetime import date
from app.services.profile_service import (
    get_user_public_events,
    get_company_public_events,
    toggle_company_subscription
)
from app.services.events_service import get_user_events
from app.forms import UserProfileForm, ChangePasswordForm

profile = Blueprint('profile', __name__)


def _save_avatar(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/uploads', picture_fn)

    output_size = (300, 300)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn


def _get_or_create_profile(user: User) -> UserProfile:
    if user.profile:
        return user.profile
    p = UserProfile(user_id=user.id)
    db.session.add(p)
    db.session.commit()
    return p


@profile.route('/me', methods=['GET', 'POST'])
@login_required
def me():
    tab = (request.args.get('tab') or 'profile').strip()
    if tab not in ('profile', 'events', 'org', 'security'):
        tab = 'profile'

    prof = _get_or_create_profile(current_user)

    profile_form = UserProfileForm(prefix='p')
    password_form = ChangePasswordForm(prefix='s')

    if request.method == 'GET':
        profile_form.full_name.data = prof.full_name
        profile_form.headline.data = prof.headline
        profile_form.bio.data = prof.bio
        profile_form.education.data = prof.education
        profile_form.work.data = prof.work

    if profile_form.submit.data and profile_form.validate_on_submit():
        prof.full_name = (profile_form.full_name.data or '').strip() or None
        prof.headline = (profile_form.headline.data or '').strip() or None
        prof.bio = (profile_form.bio.data or '').strip() or None
        prof.education = (profile_form.education.data or '').strip() or None
        prof.work = (profile_form.work.data or '').strip() or None

        if profile_form.avatar.data:
            avatar_file = _save_avatar(profile_form.avatar.data)
            prof.avatar_file = avatar_file

        db.session.commit()
        flash('Профіль оновлено!', 'success')
        return redirect(url_for('profile.me', tab='profile'))

    if password_form.submit.data and password_form.validate_on_submit():
        if not current_user.check_password(password_form.current_password.data):
            flash('Поточний пароль невірний.', 'danger')
            return redirect(url_for('profile.me', tab='security'))

        current_user.set_password(password_form.new_password.data)
        db.session.commit()
        flash('Пароль змінено!', 'success')
        return redirect(url_for('profile.me', tab='security'))

    my_events = get_user_events(current_user.id) if tab == 'events' else []

    org_request = None
    if tab == 'org' and not current_user.company_id:
        org_request = OrganizationRequest.query.filter_by(requester_id=current_user.id).order_by(
            OrganizationRequest.created_at.desc()
        ).first()

    return render_template(
        'profile/me.html',
        tab=tab,
        profile=prof,
        profile_form=profile_form,
        password_form=password_form,
        my_events=my_events,
        org_request=org_request,
    )


@profile.route('/user/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    prof = user.profile
    events = get_user_public_events(user.id)

    is_following = False
    if current_user.is_authenticated and current_user.id != user.id:
        is_following = current_user.is_following(user)

    return render_template(
        'profile/user.html',
        user=user,
        profile=prof,
        events=events,
        is_following=is_following,
        now=date.today()
    )


@profile.route('/company/<int:id>')
def company_profile(id):
    company = Company.query.get_or_404(id)
    events = get_company_public_events(company.id)

    is_subscribed = False
    if current_user.is_authenticated:
        is_subscribed = current_user.is_subscribed(company)

    return render_template('profile/company.html',
                           company=company,
                           events=events,
                           is_subscribed=is_subscribed,
                           now=date.today())


@profile.route('/company/<int:id>/subscribe', methods=['POST'])
@login_required
def toggle_subscription(id):
    company = Company.query.get_or_404(id)
    is_subscribed = toggle_company_subscription(current_user, company)
    if is_subscribed:
        flash('Ви підписались на організацію!', 'success')
    else:
        flash('Ви відписались від організації', 'info')
    return redirect(url_for('profile.company_profile', id=id))


@profile.route('/user/<username>/follow', methods=['POST'])
@login_required
def toggle_follow_user(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user.id == current_user.id:
        return redirect(url_for('profile.user_profile', username=username))

    if current_user.is_following(user):
        current_user.unfollow(user)
        db.session.commit()
        flash('Ви відписались від користувача.', 'info')
    else:
        current_user.follow(user)
        db.session.commit()
        flash('Ви підписались на користувача!', 'success')

    return redirect(url_for('profile.user_profile', username=username))