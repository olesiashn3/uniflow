from app import db
from app.models import User, Category


def register_user(username, email, password):
    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def authenticate_user(email, password):
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        return user
    return None


def complete_onboarding(user, selected_category_ids):
    user.interests = []

    if selected_category_ids:
        categories = Category.query.filter(Category.id.in_(selected_category_ids)).all()
        user.interests.extend(categories)

    user.onboarding_done = True
    db.session.commit()


def get_all_categories():
    return Category.query.all()

