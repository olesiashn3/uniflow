import os
import secrets
from PIL import Image
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Event, Category, Favorite, Question
from app.forms import EventForm
from datetime import date, timedelta, datetime

events = Blueprint('events', __name__)


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/uploads', picture_fn)

    output_size = (1200, 600)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@events.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category_id = request.args.get('category', 0, type=int)
    sort = request.args.get('sort', 'new')
    format_type = request.args.get('format', '')
    city_filter = request.args.get('city', '')

    query = Event.query.filter_by(status='approved')
    query = query.filter((Event.deadline >= date.today()) | (Event.deadline == None))

    if search:
        query = query.filter(Event.title.ilike(f'%{search}%'))
    if category_id:
        query = query.filter_by(category_id=category_id)
    if format_type:
        query = query.filter_by(format=format_type)
    if city_filter:
        query = query.filter(Event.city.ilike(f'%{city_filter}%'))

    if sort == 'deadline':
        query = query.filter(Event.deadline != None).order_by(Event.deadline.asc())
    else:
        query = query.order_by(Event.created_at.desc())

    events_list = query.paginate(page=page, per_page=9, error_out=False)
    categories = Category.query.all()

    popular_cities = [
        'Київ', 'Львів', 'Одеса', 'Харків', 'Дніпро',
        'Івано-Франківськ', 'Тернопіль', 'Вінниця', 'Луцьк', 'Чернівці'
    ]

    favorite_ids = []
    if current_user.is_authenticated:
        favorite_ids = [f.event_id for f in Favorite.query.filter_by(user_id=current_user.id).all()]

    return render_template('events/index.html',
                           events=events_list,
                           categories=categories,
                           popular_cities=popular_cities,
                           search=search,
                           current_category=category_id,
                           current_city=city_filter,
                           current_format=format_type,
                           favorite_ids=favorite_ids,
                           now=date.today())


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

    questions = event.questions.order_by(Question.created_at.desc()).all()

    return render_template('events/detail.html', event=event, is_favorite=is_favorite, questions=questions)


@events.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = EventForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]

    # ДОДАНО: Логіка вибору автора (Особисто чи від компанії)
    form.company_id.choices = [(0, f"Особисто ({current_user.username})")]
    if current_user.company:
        form.company_id.choices.append((current_user.company.id, f"Від імені: {current_user.company.name}"))

    if form.validate_on_submit():
        picture_file = None
        if form.image.data:
            picture_file = save_picture(form.image.data)

        # ДОДАНО: Визначаємо вибрану компанію
        selected_company = form.company_id.data if form.company_id.data != 0 else None

        event = Event(
            title=form.title.data,
            description=form.description.data,
            requirements=form.requirements.data,
            deadline=form.deadline.data,
            link=form.link.data,
            format=form.format.data or None,
            city=form.city.data or None,
            image_file=picture_file,
            category_id=form.category_id.data,
            company_id=selected_company,  # ДОДАЛИ СЮДИ!
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
    user_events = Event.query.filter_by(author_id=current_user.id) \
        .order_by(Event.created_at.desc()).all()
    return render_template('events/my_events.html', events=user_events)


@events.route('/event/<int:id>/ask', methods=['POST'])
@login_required
def ask_question(id):
    event = Event.query.get_or_404(id)
    question_text = request.form.get('question')

    if question_text and len(question_text.strip()) > 0:
        question = Question(text=question_text.strip(), user_id=current_user.id, event_id=event.id)
        db.session.add(question)
        db.session.commit()
        flash('Ваше запитання надіслано!', 'success')
    else:
        flash('Запитання не може бути порожнім.', 'danger')

    return redirect(url_for('events.detail', id=id))


@events.route('/question/<int:question_id>/answer', methods=['POST'])
@login_required
def answer_question(question_id):
    question = Question.query.get_or_404(question_id)
    event = question.event

    if current_user.id != event.author_id and current_user.role != 'admin':
        flash('У вас немає прав для відповіді на це запитання.', 'danger')
        return redirect(url_for('events.detail', id=event.id))

    answer_text = request.form.get('answer')
    if answer_text and len(answer_text.strip()) > 0:
        question.answer = answer_text.strip()
        question.answered_at = datetime.utcnow()
        db.session.commit()
        flash('Відповідь успішно додано!', 'success')
    else:
        flash('Відповідь не може бути порожньою.', 'danger')

    return redirect(url_for('events.detail', id=event.id))