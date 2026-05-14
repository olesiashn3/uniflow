from urllib.parse import urljoin, urlparse

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.services.auth_service import (
    register_user,
    authenticate_user,
    complete_onboarding,
    get_all_categories
)
from app.forms import LoginForm, RegisterForm

auth = Blueprint('auth', __name__)


def _safe_next_path(next_param: str | None) -> str | None:
    """Return a same-host relative path for redirect, or None if unsafe or empty."""
    if not next_param or not isinstance(next_param, str):
        return None
    target = next_param.strip()
    if not target or any(c in target for c in '\r\n'):
        return None
    if '\\' in target:
        return None
    ref = urlparse(request.host_url)
    candidate = urlparse(urljoin(request.host_url, target))
    if candidate.scheme not in ('http', 'https'):
        return None
    if ref.netloc.lower() != candidate.netloc.lower():
        return None
    path = candidate.path or '/'
    if not path.startswith('/'):
        path = '/' + path
    if candidate.query:
        path = f'{path}?{candidate.query}'
    if candidate.fragment:
        path = f'{path}#{candidate.fragment}'
    return path


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('events.index'))

    form = RegisterForm()
    if form.validate_on_submit():
        user = register_user(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data
        )

        login_user(user)
        flash('Реєстрація успішна! Налаштуймо твій простір.', 'success')

        return redirect(url_for('auth.onboarding'))

    return render_template('auth/register.html', form=form)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('events.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = authenticate_user(form.email.data, form.password.data)
        if user:
            login_user(user)
            next_page = request.args.get('next')

            if not user.onboarding_done:
                return redirect(url_for('auth.onboarding'))

            flash('Ласкаво просимо!', 'success')
            safe = _safe_next_path(next_page)
            return redirect(safe or url_for('events.index'))

        flash('Невірний email або пароль', 'danger')
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Ви вийшли з системи', 'info')
    return redirect(url_for('events.index'))


@auth.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    if request.method == 'POST':
        selected_category_ids = request.form.getlist('categories')
        complete_onboarding(current_user, selected_category_ids)

        flash('Твій простір налаштовано! 🎉', 'success')
        return redirect(url_for('events.index'))

    categories = get_all_categories()
    return render_template('auth/onboarding.html', categories=categories)