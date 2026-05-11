import os
import secrets
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request
from flask_login import login_required, current_user
from app import db
from app.models import Event, Company, OrganizationRequest, User, EventEditRequest
from app.forms import CompanyForm, AssignCompanyForm
from PIL import Image
from app.services.admin_service import (
    get_dashboard_data,
    approve_event,
    reject_event,
    create_company as create_company_record,
    toggle_company_verification,
    assign_user_to_company,
    approve_event_edit_request,
    reject_event_edit_request,
)
from app.services.notifications_service import (
    create_approval_notification,
    create_rejection_notification,
)
from app.observers.organization_approval import notify_organization_request_approved

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
    pending, pending_edits, approved, rejected, users, companies, analytics = get_dashboard_data()
    pending_org_requests_count = OrganizationRequest.query.filter_by(status='pending').count()
    return render_template('admin/dashboard.html',
                           pending=pending,
                           pending_edits=pending_edits,
                           approved_count=approved,
                           rejected_count=rejected,
                           users_count=users,
                           companies=companies,
                           analytics=analytics,
                           pending_org_requests_count=pending_org_requests_count)


@admin.route('/approve/<int:id>')
@login_required
@admin_required
def approve(id):
    event = Event.query.get_or_404(id)
    approve_event(event)
    create_approval_notification(event)
    flash(f'Подію "{event.title}" схвалено!', 'success')
    return redirect(url_for('admin.dashboard'))


@admin.route('/reject/<int:id>')
@login_required
@admin_required
def reject(id):
    event = Event.query.get_or_404(id)
    reject_event(event)
    create_rejection_notification(event)
    flash(f'Подію "{event.title}" відхилено.', 'info')
    return redirect(url_for('admin.dashboard'))


@admin.route('/event-edits/<int:request_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_event_edit(request_id):
    req = EventEditRequest.query.get_or_404(request_id)
    if req.status != 'pending':
        flash('Цей запит вже оброблено.', 'info')
        return redirect(url_for('admin.dashboard'))

    event = approve_event_edit_request(req, current_user)
    if not event:
        flash('Подію не знайдено. Неможливо застосувати зміни.', 'danger')
        return redirect(url_for('admin.dashboard'))

    flash('Зміни до події застосовано та схвалено.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin.route('/event-edits/<int:request_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_event_edit(request_id):
    req = EventEditRequest.query.get_or_404(request_id)
    if req.status != 'pending':
        flash('Цей запит вже оброблено.', 'info')
        return redirect(url_for('admin.dashboard'))

    note = (request.form.get('admin_note') or '').strip()
    reject_event_edit_request(req, current_user, admin_note=note)
    flash('Запит на редагування відхилено.', 'info')
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


@admin.route('/org-requests')
@login_required
@admin_required
def org_requests():
    status = request.args.get('status', 'pending').strip()
    if status not in ('pending', 'approved', 'rejected'):
        status = 'pending'

    reqs = OrganizationRequest.query.filter_by(status=status).order_by(OrganizationRequest.created_at.desc()).all()
    pending_count = OrganizationRequest.query.filter_by(status='pending').count()
    approved_count = OrganizationRequest.query.filter_by(status='approved').count()
    rejected_count = OrganizationRequest.query.filter_by(status='rejected').count()

    return render_template(
        'admin/org_requests.html',
        requests=reqs,
        current_status=status,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
    )


@admin.route('/org-requests/<int:request_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_org_request(request_id):
    req = OrganizationRequest.query.get_or_404(request_id)
    if req.status != 'pending':
        flash('Цей запит вже оброблено.', 'info')
        return redirect(url_for('admin.org_requests', status=req.status))

    # Create a company and bind requester as representative.
    company = create_company_record(
        name=req.company_name,
        description=None,
        website=req.social_link,
        logo_file=None,
    )

    user = User.query.get(req.requester_id)
    if user:
        user.company_id = company.id

    req.status = 'approved'
    req.decided_at = datetime.utcnow()
    req.decided_by_id = current_user.id
    req.created_company_id = company.id
    db.session.commit()

    notify_organization_request_approved(
        requester_id=req.requester_id,
        company_name=company.name,
    )

    flash(f'Запит схвалено. Організацію "{company.name}" створено та користувача привʼязано.', 'success')
    return redirect(url_for('admin.org_requests', status='pending'))


@admin.route('/org-requests/<int:request_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_org_request(request_id):
    req = OrganizationRequest.query.get_or_404(request_id)
    if req.status != 'pending':
        flash('Цей запит вже оброблено.', 'info')
        return redirect(url_for('admin.org_requests', status=req.status))

    note = (request.form.get('admin_note') or '').strip()
    req.status = 'rejected'
    req.admin_note = note or None
    req.decided_at = datetime.utcnow()
    req.decided_by_id = current_user.id

    from app import db
    db.session.commit()
    flash('Запит відхилено.', 'info')
    return redirect(url_for('admin.org_requests', status='pending'))