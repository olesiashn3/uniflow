from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ДОДАНО: Проміжна таблиця для системи підписок (Many-to-Many)
subscriptions = db.Table('subscriptions',
                         db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
                         db.Column('company_id', db.Integer, db.ForeignKey('companies.id'), primary_key=True)
                         )


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    events = db.relationship('Event', backref='author', lazy='dynamic')
    favorites = db.relationship('Favorite', backref='user', lazy='dynamic')

    # ДОДАНО: Зв'язок з питаннями та підписками
    questions = db.relationship('Question', backref='author', lazy='dynamic')
    subscribed_companies = db.relationship('Company', secondary=subscriptions,
                                           backref=db.backref('subscribers', lazy='dynamic'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


# ДОДАНО: Нова сутність - Компанія (Офіційний Хаб)
class Company(db.Model):
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    website = db.Column(db.String(255), nullable=True)
    logo_file = db.Column(db.String(255), nullable=True, default='default_company.png')
    is_verified = db.Column(db.Boolean, default=False)  # Та сама синя галочка!
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Зв'язок з подіями: Одна компанія може мати багато подій
    events = db.relationship('Event', backref='company', lazy='dynamic')

    def __repr__(self):
        return f'<Company {self.name}>'


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)

    events = db.relationship('Event', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text)
    deadline = db.Column(db.Date)
    link = db.Column(db.String(500))
    format = db.Column(db.String(10), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    image_file = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(10), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))

    # ДОДАНО: Прив'язка події до компанії (може бути порожньою, якщо це просто подія від юзера)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)

    favorites = db.relationship('Favorite', backref='event', lazy='dynamic')

    # ДОДАНО: Зв'язок з питаннями під цією подією
    questions = db.relationship('Question', backref='event', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Event {self.title}>'


class Favorite(db.Model):
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Favorite user={self.user_id} event={self.event_id}>'


# ДОДАНО: Таблиця для Q&A (Запитання-Відповіді)
class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=True)  # Відповідь компанії (спочатку порожня)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    answered_at = db.Column(db.DateTime, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Хто запитав
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)  # Під якою подією

    def __repr__(self):
        return f'<Question {self.id} on Event {self.event_id}>'