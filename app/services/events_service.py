from datetime import datetime
from typing import Any, Optional

from app import db
from app.models import Event, Favorite, Question, Company
from app.repositories.event_repository import IEventRepository, SqlAlchemyEventRepository


def build_events_query(
    search: str = "",
    category_id: int = 0,
    sort: str = "new",
    format_type: str = "",
    city_filter: str = "",
    feed: str = "all",
    user: Any = None,
    repository: Optional[IEventRepository] = None,
) -> Any:
    """Build the public events query; optional ``repository`` for tests."""
    repo = repository or SqlAlchemyEventRepository()
    return repo.build_public_events_query(
        search=search or "",
        category_id=category_id or 0,
        sort=sort or "new",
        format_type=format_type or "",
        city_filter=city_filter or "",
        feed=feed or "all",
        user=user,
    )


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
    subscribed_company_ids = {c.id for c in companies}
    all_companies = Company.query.order_by(Company.created_at.desc()).all()
    suggested_companies = [c for c in all_companies if c.id not in subscribed_company_ids][:4]

    followed_users = user.followed_users.all()
    return companies, suggested_companies, followed_users


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

