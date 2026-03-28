from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Event, Favorite

profile = Blueprint('profile', __name__)


@profile.route('/')
@login_required
def index():
    user_events = Event.query.filter_by(author_id=current_user.id).all()
    favorites_count = Favorite.query.filter_by(user_id=current_user.id).count()
    approved = sum(1 for e in user_events if e.status == 'approved')
    pending = sum(1 for e in user_events if e.status == 'pending')
    rejected = sum(1 for e in user_events if e.status == 'rejected')

    return render_template('profile/index.html',
                           user_events=user_events,
                           favorites_count=favorites_count,
                           approved=approved,
                           pending=pending,
                           rejected=rejected)