from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Event, Category, Favorite
from app.forms import EventForm
from datetime import date, timedelta

events = Blueprint('events', __name__)


@events.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category_id = request.args.get('category', 0, type=int)
    sort = request.args.get('sort', 'new')
    format_type = request.args.get('format', '')

    # Обираємо тільки схвалені події
    query = Event.query.filter_by(status='approved')

    # ДОДАНО: Фільтруємо прострочені події (показуємо лише ті, де дедлайн у майбутньому або відсутній)
    # Зверни увагу: треба імпортувати date з datetime (вже має бути в файлі)
    query = query.filter((Event.deadline >= date.today()) | (Event.deadline == None))

    if search:
        query = query.filter(Event.title.ilike(f'%{search}%'))

    if category_id:
        query = query.filter_by(category_id=category_id)

    if format_type in ['online', 'offline']:
        query = query.filter_by(format=format_type)

    if sort == 'deadline':
        query = query.filter(Event.deadline != None).order_by(Event.deadline.asc())
    else:
        query = query.order_by(Event.created_at.desc())

    events_list = query.paginate(page=page, per_page=9, error_out=False)
    # ... решта коду залишається без змін ...
    categories = Category.query.all()

    favorite_ids = []
    if current_user.is_authenticated:
        favorite_ids = [f.event_id for f in Favorite.query.filter_by(user_id=current_user.id).all()]

    upcoming = Event.query.filter_by(status='approved')\
        .filter(Event.deadline != None)\
        .filter(Event.deadline >= date.today())\
        .filter(Event.deadline <= date.today() + timedelta(days=30))\
        .order_by(Event.deadline.asc())\
        .limit(10).all()

    return render_template('events/index.html',
                           events=events_list,
                           categories=categories,
                           search=search,
                           current_category=category_id,
                           favorite_ids=favorite_ids,
                           now=date.today(),
                           upcoming=upcoming)


@events.route('/event/<int:id>')
def detail(id):
    event = Event.query.get_or_404(id)
    if event.status != 'approved' and (
        not current_user.is_authenticated or
        current_user.role != 'admin' and current_user.id != event.author_id
    ):
        flash('Подія не знайдена', 'danger')
        return redirect(url_for('events.index'))

    is_favorite = False
    if current_user.is_authenticated:
        is_favorite = Favorite.query.filter_by(
            user_id=current_user.id,
            event_id=event.id
        ).first() is not None

    return render_template('events/detail.html', event=event, is_favorite=is_favorite)


@events.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = EventForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]

    if form.validate_on_submit():
        event = Event(
            title=form.title.data,
            description=form.description.data,
            requirements=form.requirements.data,
            deadline=form.deadline.data,
            link=form.link.data,
            format=form.format.data or None,
            city=form.city.data or None,
            category_id=form.category_id.data,
            author_id=current_user.id,
            status='pending'
        )
        db.session.add(event)
        db.session.commit()
        flash('Подію додано! Очікує на перевірку адміністратором.', 'success')
        return redirect(url_for('events.index'))

    return render_template('events/add.html', form=form)


@events.route('/my-events')
@login_required
def my_events():
    user_events = Event.query.filter_by(author_id=current_user.id)\
        .order_by(Event.created_at.desc()).all()
    return render_template('events/my_events.html', events=user_events)