from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from app.models import Event
from datetime import date
from app.services.favorites_service import get_user_favorites, toggle_favorite

favorites = Blueprint('favorites', __name__)


@favorites.route('/')
@login_required
def index():
    user_favorites = get_user_favorites(current_user.id)

    return render_template('favorites/index.html',
                           favorites=user_favorites,
                           now=date.today())


@favorites.route('/toggle/<int:event_id>', methods=['POST'])
@login_required
def toggle(event_id):
    Event.query.get_or_404(event_id)
    is_favorite = toggle_favorite(current_user.id, event_id)
    message = 'Додано до вибраного!' if is_favorite else 'Видалено з вибраного'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'is_favorite': is_favorite, 'message': message})

    flash(message, 'success')
    return redirect(request.referrer or url_for('events.detail', id=event_id))