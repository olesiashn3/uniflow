from datetime import date, datetime

from app import db
from app.models import Event, Favorite, Question, Company, User
from sqlalchemy import or_


def build_events_query(search='', category_id=0, sort='new', format_type='', city_filter='', feed='all', user=None):
    query = Event.query.filter_by(status='approved')
    query = query.filter((Event.deadline >= date.today()) | (Event.deadline == None))

    if feed == 'foryou' and user and user.is_authenticated:
        interest_ids = [category.id for category in user.interests]
        favorites = user.favorites.all()
        activity_cat_ids = [fav.event.category_id for fav in favorites if fav.event and fav.event.category_id]
        recommended_category_ids = list(set(interest_ids + activity_cat_ids))

        if recommended_category_ids:
            query = query.filter(Event.category_id.in_(recommended_category_ids))
        else:
            query = query.filter(Event.id < 0)
    elif feed == 'subscriptions' and user and user.is_authenticated:
        subscribed_company_ids = [company.id for company in user.subscribed_companies]
        followed_user_ids = [u.id for u in user.followed_users.all()]

        if subscribed_company_ids or followed_user_ids:
            parts = []
            if subscribed_company_ids:
                parts.append(Event.company_id.in_(subscribed_company_ids))
            if followed_user_ids:
                parts.append(Event.author_id.in_(followed_user_ids))

            # SQLAlchemy OR across parts
            if len(parts) == 1:
                query = query.filter(parts[0])
            else:
                query = query.filter(or_(*parts))
        else:
            query = query.filter(Event.id < 0)

    if search:
        query = query.filter(Event.title.ilike(f'%{search}%'))
    if category_id > 0:
        query = query.filter(Event.category_id == category_id)
    if format_type:
        query = query.filter_by(format=format_type)
    if city_filter:
        query = query.filter(Event.city.ilike(f'%{city_filter}%'))

    if sort == 'deadline':
        query = query.filter(Event.deadline != None).order_by(Event.deadline.asc())
    else:
        query = query.order_by(Event.created_at.desc())

    return query


def create_event_from_form(form, author_id, image_file):
    selected_company = form.company_id.data if form.company_id.data != 0 else None
    event = Event(
        title=form.title.data,
        description=form.description.data,
        requirements=form.requirements.data,
        deadline=form.deadline.data,
        link=form.link.data,
        format=form.format.data or None,
        city=form.city.data or None,
        image_file=image_file,
        category_id=form.category_id.data,
        company_id=selected_company,
        author_id=author_id,
        status='pending'
    )
    db.session.add(event)
    db.session.commit()
    return event


def get_user_events(user_id):
    return Event.query.filter_by(author_id=user_id).order_by(Event.created_at.desc()).all()


def get_user_subscriptions_data(user):
    companies = user.subscribed_companies
    all_companies = Company.query.all()
    suggested_companies = [c for c in all_companies if c not in companies][:4]
    followed_users = user.followed_users.all()
    suggested_users = User.query.filter(User.id != user.id).all()
    suggested_users = [u for u in suggested_users if u not in followed_users][:6]
    return companies, suggested_companies, followed_users, suggested_users


def toggle_company_subscription(user, company):
    if user.is_subscribed(company):
        user.subscribed_companies.remove(company)
        subscribed = False
    else:
        user.subscribed_companies.append(company)
        subscribed = True
    db.session.commit()
    return subscribed


def create_question(event_id, user_id, text):
    question = Question(text=text.strip(), user_id=user_id, event_id=event_id)
    db.session.add(question)
    db.session.commit()
    return question


def answer_question(question, answer_text):
    question.answer = answer_text.strip()
    question.answered_at = datetime.utcnow()
    db.session.commit()
    return question


def is_event_visible_for_user(event, user):
    if event.status == 'approved':
        return True
    if not user.is_authenticated:
        return False
    return user.role == 'admin' or user.id == event.author_id


def get_event_favorite_status(event_id, user_id):
    return Favorite.query.filter_by(user_id=user_id, event_id=event_id).first() is not None


def get_event_questions(event):
    return event.questions.order_by(Question.created_at.desc()).all()


def get_user_favorite_event_ids(user):
    return [f.event_id for f in user.favorites.all()]

