from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Category  # Додали імпорт Category
from app.forms import LoginForm, RegisterForm

auth = Blueprint('auth', __name__)


@auth.route('/register', methods=['GET', 'POST'])
def register():
    # Якщо вже залогінений — на головну
    if current_user.is_authenticated:
        return redirect(url_for('events.index'))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        # Одразу логінимо юзера після успішної реєстрації (так зручніше UX)
        login_user(user)
        flash('Реєстрація успішна! Налаштуймо твій простір.', 'success')

        # Кидаємо на сторінку онбордінгу
        return redirect(url_for('auth.onboarding'))

    return render_template('auth/register.html', form=form)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('events.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')

            # Якщо користувач ще не пройшов онбордінг — кидаємо його туди
            if not user.onboarding_done:
                return redirect(url_for('auth.onboarding'))

            flash('Ласкаво просимо!', 'success')
            return redirect(next_page or url_for('events.index'))

        flash('Невірний email або пароль', 'danger')
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Ви вийшли з системи', 'info')
    return redirect(url_for('events.index'))


# НОВИЙ РОУТ ДЛЯ ОНБОРДІНГУ
@auth.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    if request.method == 'POST':
        # Отримуємо список ID вибраних категорій з форми
        selected_category_ids = request.form.getlist('categories')

        # Очищаємо старі інтереси (якщо юзер перепроходить)
        current_user.interests = []

        # Якщо щось вибрали — додаємо нові
        if selected_category_ids:
            categories = Category.query.filter(Category.id.in_(selected_category_ids)).all()
            current_user.interests.extend(categories)

        # Відмічаємо, що онбордінг пройдено
        current_user.onboarding_done = True
        db.session.commit()

        flash('Твій простір налаштовано! 🎉', 'success')
        return redirect(url_for('events.index'))

    # Для GET-запиту просто дістаємо всі категорії і показуємо сторінку
    categories = Category.query.all()
    return render_template('auth/onboarding.html', categories=categories)