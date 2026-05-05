import os
import secrets
import urllib.parse
from PIL import Image
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import text
from app import db
from app.models import Event, Category, Company, Favorite, Notification, Question, EventEditRequest
from app.forms import EventForm, EventEditForm
from datetime import date
from app.services.events_service import (
    build_events_query,
    create_event_from_form,
    get_user_events,
    get_user_subscriptions_data,
    toggle_company_subscription,
    create_question,
    answer_question as answer_question_service,
    is_event_visible_for_user,
    get_event_favorite_status,
    get_event_questions,
    get_user_favorite_event_ids
)

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
    search = request.args.get('search', '').strip()
    category_id = request.args.get('category', 0, type=int)
    sort = request.args.get('sort', 'new')
    format_type = request.args.get('format', '').strip()
    city_filter = request.args.get('city', '').strip()
    feed = request.args.get('feed', 'all')  # Параметр стрічки

    query = build_events_query(
        search=search,
        category_id=category_id,
        sort=sort,
        format_type=format_type,
        city_filter=city_filter,
        feed=feed,
        user=current_user
    )

    events_list = query.paginate(page=page, per_page=9, error_out=False)

    # Сортуємо категорії за алфавітом
    categories = Category.query.order_by(Category.name.asc()).all()

    popular_cities = [
        'Київ', 'Львів', 'Одеса', 'Харків', 'Дніпро',
        'Івано-Франківськ', 'Тернопіль', 'Вінниця', 'Луцьк', 'Чернівці'
    ]

    favorite_ids = []
    if current_user.is_authenticated:
        favorite_ids = get_user_favorite_event_ids(current_user)

    return render_template('events/index.html',
                           events=events_list,
                           categories=categories,
                           popular_cities=popular_cities,
                           search=search,
                           current_category=category_id,
                           current_city=city_filter,
                           current_format=format_type,
                           current_feed=feed,
                           favorite_ids=favorite_ids,
                           now=date.today())


@events.route('/event/<int:id>')
def detail(id):
    event = Event.query.get_or_404(id)
    if not is_event_visible_for_user(event, current_user):
        flash('Подія не знайдена', 'danger')
        return redirect(url_for('events.index'))

    is_favorite = False
    if current_user.is_authenticated:
        is_favorite = get_event_favorite_status(event.id, current_user.id)

    questions = get_event_questions(event)

    # Google Calendar link (all-day on deadline date; fallback to today)
    base_url = "https://calendar.google.com/calendar/render"
    start_date = (event.deadline or date.today())
    end_date = start_date.toordinal() + 1
    end_date = date.fromordinal(end_date)
    dates = f"{start_date.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"

    details_parts = [event.description.strip()]
    if event.link:
        details_parts.append("")
        details_parts.append(f"Посилання: {event.link}")
    details = "\n".join([p for p in details_parts if p is not None])

    location = None
    if event.format == 'online':
        location = 'Онлайн'
    elif event.city:
        location = event.city

    params = {
        "action": "TEMPLATE",
        "text": event.title,
        "dates": dates,
        "details": details,
        "ctz": "Europe/Kyiv",
    }
    if location:
        params["location"] = location

    google_calendar_url = f"{base_url}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"

    return render_template(
        'events/detail.html',
        event=event,
        is_favorite=is_favorite,
        questions=questions,
        google_calendar_url=google_calendar_url,
    )


@events.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = EventForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]

    form.company_id.choices = [(0, f"Особисто ({current_user.username})")]
    if current_user.company:
        form.company_id.choices.append((current_user.company.id, f"Від імені: {current_user.company.name}"))

    if form.validate_on_submit():
        picture_file = None
        if form.image.data:
            picture_file = save_picture(form.image.data)
        create_event_from_form(form, current_user.id, picture_file)
        flash('Подію додано! Очікує на перевірку адміністратором.', 'success')
        return redirect(url_for('events.index'))

    return render_template('events/add.html', form=form)


@events.route('/my-events')
@login_required
def my_events():
    # Moved into "Мій профіль" (cabinet) to keep top nav clean.
    return redirect(url_for('profile.me', tab='events'))


@events.route('/event/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(id):
    event = Event.query.get_or_404(id)
    if current_user.id != event.author_id and current_user.role != 'admin':
        flash('У вас немає прав для редагування цієї події.', 'danger')
        return redirect(url_for('events.detail', id=id))

    form = EventEditForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    form.company_id.choices = [(0, f"Особисто ({current_user.username})")]
    if current_user.company:
        form.company_id.choices.append((current_user.company.id, f"Від імені: {current_user.company.name}"))

    if request.method == 'GET':
        form.title.data = event.title
        form.description.data = event.description
        form.requirements.data = event.requirements
        form.deadline.data = event.deadline
        form.link.data = event.link
        form.format.data = event.format or ''
        form.city.data = event.city
        form.category_id.data = event.category_id
        form.company_id.data = event.company_id or 0

    if form.validate_on_submit():
        picture_file = event.image_file
        if form.image.data:
            picture_file = save_picture(form.image.data)

        selected_company = form.company_id.data if form.company_id.data != 0 else None

        req = EventEditRequest(
            event_id=event.id,
            requester_id=current_user.id,
            status='pending',
            title=form.title.data,
            description=form.description.data,
            requirements=form.requirements.data,
            deadline=form.deadline.data,
            link=form.link.data,
            format=form.format.data or None,
            city=form.city.data or None,
            image_file=picture_file,
            category_id=form.category_id.data,
            company_id=selected_company,
        )
        db.session.add(req)
        db.session.commit()

        flash('Зміни надіслано на перевірку модератором.', 'success')
        return redirect(url_for('profile.me', tab='events'))

    return render_template('events/edit.html', form=form, event=event)

@events.route('/event/<int:id>/delete', methods=['POST'])
@login_required
def delete_event(id):
    event = Event.query.get_or_404(id)

    if current_user.id != event.author_id and current_user.role != 'admin':
        flash('У вас немає прав для видалення цієї події.', 'danger')
        return redirect(request.referrer or url_for('events.my_events'))

    # Cleanup dependent rows to avoid FK issues
    Favorite.query.filter_by(event_id=event.id).delete(synchronize_session=False)
    Notification.query.filter_by(event_id=event.id).delete(synchronize_session=False)
    # If DB has extra child tables (e.g. MySQL event_images) not modeled in ORM, clear them too
    try:
        db.session.execute(text("DELETE FROM event_images WHERE event_id = :event_id"), {"event_id": event.id})
    except Exception:
        # Table might not exist in some environments
        pass

    # Remove uploaded cover if present (best-effort)
    if event.image_file:
        try:
            picture_path = os.path.join(current_app.root_path, 'static', 'uploads', event.image_file)
            if os.path.exists(picture_path):
                os.remove(picture_path)
        except Exception:
            pass

    db.session.delete(event)
    db.session.commit()
    flash('Подію видалено.', 'success')
    return redirect(url_for('events.my_events'))


@events.route('/subscriptions')
@login_required
def subscriptions():
    companies, suggested_companies, followed_users = get_user_subscriptions_data(current_user)

    return render_template('events/subscriptions.html',
                           companies=companies,
                           suggested_companies=suggested_companies,
                           followed_users=followed_users)


@events.route('/company/<int:id>/toggle_subscribe', methods=['POST'])
@login_required
def toggle_subscribe(id):
    company = Company.query.get_or_404(id)
    is_subscribed = toggle_company_subscription(current_user, company)
    if is_subscribed:
        flash(f'Ви підписалися на {company.name}', 'success')
    else:
        flash(f'Ви відписалися від {company.name}', 'info')
    # Повертаємо туди, звідки прийшов юзер
    return redirect(request.referrer or url_for('events.index'))


@events.route('/event/<int:id>/ask', methods=['POST'])
@login_required
def ask_question(id):
    event = Event.query.get_or_404(id)
    question_text = request.form.get('question')

    if question_text and len(question_text.strip()) > 0:
        create_question(event.id, current_user.id, question_text)
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
        answer_question_service(question, answer_text)
        flash('Відповідь успішно додано!', 'success')
    else:
        flash('Відповідь не може бути порожньою.', 'danger')

    return redirect(url_for('events.detail', id=event.id))