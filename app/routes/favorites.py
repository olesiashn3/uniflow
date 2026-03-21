from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Favorite, Event

favorites = Blueprint('favorites', __name__)


@favorites.route('/')
@login_required
def index():
    user_favorites = Favorite.query.filter_by(user_id=current_user.id)\
        .order_by(Favorite.created_at.desc()).all()
    return render_template('favorites/index.html', favorites=user_favorites)


@favorites.route('/toggle/<int:event_id>', methods=['POST'])
@login_required
def toggle(event_id):
    event = Event.query.get_or_404(event_id)
    favorite = Favorite.query.filter_by(
        user_id=current_user.id,
        event_id=event_id
    ).first()

    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        is_favorite = False
        message = 'Видалено з вибраного'
    else:
        new_favorite = Favorite(user_id=current_user.id, event_id=event_id)
        db.session.add(new_favorite)
        db.session.commit()
        is_favorite = True
        message = 'Додано до вибраного!'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'is_favorite': is_favorite, 'message': message})

    flash(message, 'success')
    return redirect(url_for('events.detail', id=event_id))