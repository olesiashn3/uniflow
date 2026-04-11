from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import User, Event, Company, Favorite
from datetime import date

profile = Blueprint('profile', __name__)


@profile.route('/user/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()

    # ДОДАНО: Фільтр за дедлайном для профілю юзера
    events = Event.query.filter_by(
        author_id=user.id,
        status='approved'
    ).filter((Event.deadline >= date.today()) | (Event.deadline == None)).order_by(Event.created_at.desc()).all()

    return render_template('profile/user.html', user=user, events=events, now=date.today())


@profile.route('/company/<int:id>')
def company_profile(id):
    company = Company.query.get_or_404(id)

    # ДОДАНО: Фільтр за дедлайном для профілю компанії
    events = Event.query.filter_by(
        company_id=company.id,
        status='approved'
    ).filter((Event.deadline >= date.today()) | (Event.deadline == None)).order_by(Event.created_at.desc()).all()

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

    if current_user.is_subscribed(company):
        current_user.subscribed_companies.remove(company)
        flash('Ви відписались від організації', 'info')
    else:
        current_user.subscribed_companies.append(company)
        flash('Ви підписались на організацію!', 'success')

    db.session.commit()
    return redirect(url_for('profile.company_profile', id=id))