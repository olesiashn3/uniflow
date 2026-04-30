from datetime import date

from app import db
from app.models import Event


def get_user_public_events(user_id):
    return Event.query.filter_by(
        author_id=user_id,
        status='approved'
    ).filter((Event.deadline >= date.today()) | (Event.deadline == None)).order_by(Event.created_at.desc()).all()


def get_company_public_events(company_id):
    return Event.query.filter_by(
        company_id=company_id,
        status='approved'
    ).filter((Event.deadline >= date.today()) | (Event.deadline == None)).order_by(Event.created_at.desc()).all()


def toggle_company_subscription(user, company):
    if user.is_subscribed(company):
        user.subscribed_companies.remove(company)
        db.session.commit()
        return False
    user.subscribed_companies.append(company)
    db.session.commit()
    return True

