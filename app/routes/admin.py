from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Event, User

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


@admin.route('/')
@login_required
@admin_required
def dashboard():
    pending = Event.query.filter_by(status='pending').order_by(Event.created_at.desc()).all()
    approved = Event.query.filter_by(status='approved').count()
    rejected = Event.query.filter_by(status='rejected').count()
    users = User.query.count()
    return render_template('admin/dashboard.html',
                           pending=pending,
                           approved_count=approved,
                           rejected_count=rejected,
                           users_count=users)


@admin.route('/approve/<int:id>')
@login_required
@admin_required
def approve(id):
    event = Event.query.get_or_404(id)
    event.status = 'approved'
    db.session.commit()
    flash(f'Подію "{event.title}" схвалено!', 'success')
    return redirect(url_for('admin.dashboard'))


@admin.route('/reject/<int:id>')
@login_required
@admin_required
def reject(id):
    event = Event.query.get_or_404(id)
    event.status = 'rejected'
    db.session.commit()
    flash(f'Подію "{event.title}" відхилено.', 'info')
    return redirect(url_for('admin.dashboard'))