from app import db
from app.models import Favorite


def get_user_favorites(user_id):
    return Favorite.query.filter_by(user_id=user_id).order_by(Favorite.created_at.desc()).all()


def toggle_favorite(user_id, event_id):
    favorite = Favorite.query.filter_by(user_id=user_id, event_id=event_id).first()
    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        return False

    new_favorite = Favorite(user_id=user_id, event_id=event_id)
    db.session.add(new_favorite)
    db.session.commit()
    return True

