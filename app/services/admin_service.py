from datetime import date, timedelta, datetime

from app import db
from app.models import Event, User, Company, Category


def get_dashboard_data():
    pending = Event.query.filter_by(status='pending').order_by(Event.created_at.desc()).all()
    approved = Event.query.filter_by(status='approved').count()
    rejected = Event.query.filter_by(status='rejected').count()
    users = User.query.count()
    companies = Company.query.order_by(Company.created_at.desc()).all()
    total_events = Event.query.count()
    verified_companies = Company.query.filter_by(is_verified=True).count()

    reviewed = approved + rejected
    approval_rate = round((approved / reviewed) * 100, 1) if reviewed else 0
    verification_rate = round((verified_companies / len(companies)) * 100, 1) if companies else 0

    stale_pending_count = Event.query.filter(
        Event.status == 'pending',
        Event.created_at < (datetime.utcnow() - timedelta(days=7))
    ).count()

    # Trend for the last 30 days (events created per day by status)
    start_date = date.today() - timedelta(days=29)
    start_dt = datetime.combine(start_date, datetime.min.time())
    trend_rows = db.session.query(
        db.func.date(Event.created_at).label('day'),
        Event.status,
        db.func.count(Event.id).label('count')
    ).filter(
        Event.created_at >= start_dt
    ).group_by(
        db.func.date(Event.created_at), Event.status
    ).all()

    trend_map = {}
    for row in trend_rows:
        day_key = str(row.day)
        if day_key not in trend_map:
            trend_map[day_key] = {'day': day_key, 'approved': 0, 'pending': 0, 'rejected': 0}
        trend_map[day_key][row.status] = row.count

    trend = []
    for i in range(30):
        d = start_date + timedelta(days=i)
        key = d.isoformat()
        trend.append(trend_map.get(key, {'day': key, 'approved': 0, 'pending': 0, 'rejected': 0}))

    # Top categories by approved events
    top_categories_rows = db.session.query(
        Category.name,
        db.func.count(Event.id).label('count')
    ).join(
        Event, Event.category_id == Category.id
    ).filter(
        Event.status == 'approved'
    ).group_by(
        Category.id, Category.name
    ).order_by(
        db.func.count(Event.id).desc()
    ).limit(5).all()

    top_categories = [{'name': row.name, 'count': row.count} for row in top_categories_rows]

    # Top companies by published events
    top_companies_rows = db.session.query(
        Company.name,
        db.func.count(Event.id).label('count')
    ).join(
        Event, Event.company_id == Company.id
    ).filter(
        Event.status == 'approved'
    ).group_by(
        Company.id, Company.name
    ).order_by(
        db.func.count(Event.id).desc()
    ).limit(5).all()

    top_companies = [{'name': row.name, 'count': row.count} for row in top_companies_rows]

    analytics = {
        'total_events': total_events,
        'verified_companies': verified_companies,
        'approval_rate': approval_rate,
        'verification_rate': verification_rate,
        'stale_pending_count': stale_pending_count,
        'trend': trend,
        'trend_max': max([1] + [max(day['approved'], day['pending'], day['rejected']) for day in trend]),
        'top_categories': top_categories,
        'top_companies': top_companies,
    }

    return pending, approved, rejected, users, companies, analytics


def approve_event(event):
    event.status = 'approved'
    db.session.commit()


def reject_event(event):
    event.status = 'rejected'
    db.session.commit()


def create_company(name, description=None, website=None, logo_file=None):
    company = Company(
        name=name,
        description=description,
        website=website or None,
        logo_file=logo_file
    )
    db.session.add(company)
    db.session.commit()
    return company


def toggle_company_verification(company):
    company.is_verified = not company.is_verified
    db.session.commit()
    return company.is_verified


def assign_user_to_company(username, company_id):
    user = User.query.filter_by(username=username).first()
    if not user:
        return None, None

    company = Company.query.get(company_id)
    user.company_id = company.id
    db.session.commit()
    return user, company

