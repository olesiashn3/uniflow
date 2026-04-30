from __future__ import annotations

from typing import List, Optional

from app import db
from app.models import NewsPost, Company, User


def get_news_for_user_subscriptions(user: User, limit: int = 5) -> List[NewsPost]:
    if not user or not getattr(user, "is_authenticated", False):
        return []

    subscribed_ids = [c.id for c in user.subscribed_companies]
    if not subscribed_ids:
        return []

    return (
        NewsPost.query
        .filter(NewsPost.company_id.in_(subscribed_ids))
        .order_by(NewsPost.created_at.desc())
        .limit(limit)
        .all()
    )


def get_company_news(company_id: int, limit: int = 5) -> List[NewsPost]:
    return (
        NewsPost.query
        .filter_by(company_id=company_id)
        .order_by(NewsPost.created_at.desc())
        .limit(limit)
        .all()
    )


def create_news_post(company: Company, title: str, body: str, image_file: Optional[str] = None) -> NewsPost:
    post = NewsPost(
        company_id=company.id,
        title=title.strip(),
        body=body.strip(),
        image_file=image_file,
    )
    db.session.add(post)
    db.session.commit()
    return post

