from datetime import date

from app.models import Event

from app.services.events_service import toggle_company_subscription  # re-export for consistency


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
