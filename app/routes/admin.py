import os
import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models import Event, Company
from app.forms import CompanyForm, AssignCompanyForm
from PIL import Image
from app.services.admin_service import (
    get_dashboard_data,
    approve_event,
    reject_event,
    create_company as create_company_record,
    toggle_company_verification,
    assign_user_to_company
)

admin = Blueprint('admin', __name__)


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Доступ заборонено', 'danger')
            return redirect(url_for('events.index'))
        return f(*args, **kwargs)
    return decorated_function


def save_logo(form_logo):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_logo.filename)
    logo_fn = random_hex + f_ext
    logo_path = os.path.join(current_app.root_path, 'static/uploads', logo_fn)
    output_size = (300, 300)
    i = Image.open(form_logo)
    i.thumbnail(output_size)
    i.save(logo_path)
    return logo_fn


@admin.route('/')
@login_required
@admin_required
def dashboard():
    pending, approved, rejected, users, companies, analytics = get_dashboard_data()
    return render_template('admin/dashboard.html',
                           pending=pending,
                           approved_count=approved,
                           rejected_count=rejected,
                           users_count=users,
                           companies=companies,
                           analytics=analytics)


@admin.route('/approve/<int:id>')
@login_required
@admin_required
def approve(id):
    event = Event.query.get_or_404(id)
    approve_event(event)
    flash(f'Подію "{event.title}" схвалено!', 'success')
    return redirect(url_for('admin.dashboard'))


@admin.route('/reject/<int:id>')
@login_required
@admin_required
def reject(id):
    event = Event.query.get_or_404(id)
    reject_event(event)
    flash(f'Подію "{event.title}" відхилено.', 'info')
    return redirect(url_for('admin.dashboard'))


@admin.route('/companies/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_company():
    form = CompanyForm()
    if form.validate_on_submit():
        logo_file = None
        if form.logo.data:
            logo_file = save_logo(form.logo.data)

        company = create_company_record(
            name=form.name.data,
            description=form.description.data,
            website=form.website.data,
            logo_file=logo_file
        )
        flash(f'Організацію "{company.name}" створено!', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/create_company.html', form=form)


@admin.route('/companies/verify/<int:id>')
@login_required
@admin_required
def verify_company(id):
    company = Company.query.get_or_404(id)
    is_verified = toggle_company_verification(company)
    status = 'верифіковано' if is_verified else 'верифікацію знято'
    flash(f'Організацію "{company.name}" {status}!', 'success')
    return redirect(url_for('admin.dashboard'))


@admin.route('/companies/assign', methods=['GET', 'POST'])
@login_required
@admin_required
def assign_company():
    form = AssignCompanyForm()
    form.company_id.choices = [(c.id, c.name) for c in Company.query.all()]

    if form.validate_on_submit():
        user, company = assign_user_to_company(form.username.data, form.company_id.data)
        if not user:
            flash('Користувача не знайдено', 'danger')
            return redirect(url_for('admin.assign_company'))
        flash(f'Користувача "{user.username}" прив\'язано до "{company.name}"!', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/assign_company.html', form=form)