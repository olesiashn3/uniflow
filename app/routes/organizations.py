from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from app.forms import OrganizationRequestForm
from app.models import OrganizationRequest


organizations = Blueprint('organizations', __name__)


@organizations.route('/organizations/request', methods=['GET', 'POST'])
@login_required
def request_create():
    # If user is already a company representative, don't allow duplicate requests.
    if current_user.company_id:
        flash('Ви вже привʼязані до організації. Якщо потрібно змінити дані — напишіть адміністратору.', 'info')
        return redirect(url_for('profile.user_profile', username=current_user.username))

    # If there is already a pending request, block duplicates.
    existing = OrganizationRequest.query.filter_by(requester_id=current_user.id, status='pending').first()
    if existing:
        flash('Ваш запит уже на розгляді. Очікуйте рішення адміністратора.', 'info')
        return redirect(url_for('profile.user_profile', username=current_user.username))

    form = OrganizationRequestForm()
    if form.validate_on_submit():
        req = OrganizationRequest(
            requester_id=current_user.id,
            company_name=form.company_name.data.strip(),
            social_link=(form.social_link.data.strip() if form.social_link.data else None),
            contact_email=form.contact_email.data.strip(),
            comment=(form.comment.data.strip() if form.comment.data else None),
            status='pending',
            created_at=datetime.utcnow(),
        )
        db.session.add(req)
        db.session.commit()
        flash('Запит на створення організації надіслано. Ми повідомимо вас після рішення адміністратора.', 'success')
        return redirect(url_for('events.index'))

    return render_template('organizations/request.html', form=form)

