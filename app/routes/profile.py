from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import User, Company
from datetime import date
from app.services.profile_service import (
    get_user_public_events,
    get_company_public_events,
    toggle_company_subscription
)

profile = Blueprint('profile', __name__)


@profile.route('/user/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    events = get_user_public_events(user.id)

    return render_template('profile/user.html', user=user, events=events, now=date.today())


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