from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


subscriptions = db.Table('subscriptions',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('company_id', db.Integer, db.ForeignKey('companies.id'), primary_key=True)
)

user_follows = db.Table(
    'user_follows',
    db.Column('follower_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
)

user_interests = db.Table('user_interests',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id'), primary_key=True)
)


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    onboarding_done = db.Column(db.Boolean, default=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)

    company = db.relationship('Company', foreign_keys=[company_id], backref='members')
    events = db.relationship('Event', backref='author', lazy='dynamic')
    favorites = db.relationship('Favorite', backref='user', lazy='dynamic')
    questions = db.relationship('Question', backref='author', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic',
                                    cascade='all, delete-orphan')
    interests = db.relationship('Category', secondary=user_interests, lazy='subquery',
                                backref=db.backref('interested_users', lazy=True))
    subscribed_companies = db.relationship('Company', secondary=subscriptions,
                                           foreign_keys=[subscriptions.c.user_id, subscriptions.c.company_id],
                                           backref=db.backref('subscribers', lazy='dynamic'))
    profile = db.relationship(
        'UserProfile',
        uselist=False,
        backref='user',
        lazy='joined',
        cascade='all, delete-orphan',
    )

    followed_users = db.relationship(
        'User',
        secondary=user_follows,
        primaryjoin=(user_follows.c.follower_id == id),
        secondaryjoin=(user_follows.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic',
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_subscribed(self, company):
        return company in self.subscribed_companies

    def is_following(self, other_user):
        if not other_user:
            return False
        return self.followed_users.filter(user_follows.c.followed_id == other_user.id).count() > 0

    def follow(self, other_user):
        if other_user and other_user.id != self.id and not self.is_following(other_user):
            self.followed_users.append(other_user)

    def unfollow(self, other_user):
        if other_user and self.is_following(other_user):
            self.followed_users.remove(other_user)

    def __repr__(self):
        return f'<User {self.username}>'


class Company(db.Model):
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    website = db.Column(db.String(255), nullable=True)
    logo_file = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    events = db.relationship('Event', backref='company', lazy='dynamic')
    news_posts = db.relationship('NewsPost', backref='company', lazy='dynamic',
                                 cascade='all, delete-orphan')

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
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)

    favorites = db.relationship('Favorite', backref='event', lazy='dynamic',
                                cascade='all, delete-orphan')
    questions = db.relationship('Question', backref='event', lazy='dynamic',
                                cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='event', lazy='dynamic',
                                    cascade='all, delete-orphan')

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


class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    answered_at = db.Column(db.DateTime, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)

    def __repr__(self):
        return f'<Question {self.id} on Event {self.event_id}>'


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True, index=True)

    def __repr__(self):
        return f'<Notification {self.type} for User {self.user_id}>'


class NewsPost(db.Model):
    __tablename__ = 'news_posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    image_file = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)

    def __repr__(self):
        return f'<NewsPost {self.id} company={self.company_id}>'


class OrganizationRequest(db.Model):
    __tablename__ = 'organization_requests'

    id = db.Column(db.Integer, primary_key=True)

    company_name = db.Column(db.String(140), nullable=False)
    social_link = db.Column(db.String(500), nullable=True)
    contact_email = db.Column(db.String(120), nullable=False)
    comment = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(10), default='pending', nullable=False)
    admin_note = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    decided_at = db.Column(db.DateTime, nullable=True)

    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    requester = db.relationship(
        'User',
        foreign_keys=[requester_id],
        backref=db.backref('organization_requests', lazy='dynamic')
    )

    decided_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    decided_by = db.relationship('User', foreign_keys=[decided_by_id])

    created_company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, index=True)
    created_company = db.relationship('Company', foreign_keys=[created_company_id])

    def __repr__(self):
        return f'<OrganizationRequest {self.id} status={self.status}>'


class UserProfile(db.Model):
    __tablename__ = 'user_profiles'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)

    full_name = db.Column(db.String(140), nullable=True)
    headline = db.Column(db.String(160), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    education = db.Column(db.String(200), nullable=True)
    work = db.Column(db.String(200), nullable=True)
    avatar_file = db.Column(db.String(255), nullable=True)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<UserProfile user_id={self.user_id}>'


class EventEditRequest(db.Model):
    __tablename__ = 'event_edit_requests'

    id = db.Column(db.Integer, primary_key=True)

    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    event = db.relationship('Event', foreign_keys=[event_id])

    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    requester = db.relationship('User', foreign_keys=[requester_id])

    status = db.Column(db.String(12), default='pending', nullable=False)
    admin_note = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    decided_at = db.Column(db.DateTime, nullable=True)

    decided_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    decided_by = db.relationship('User', foreign_keys=[decided_by_id])

    title = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    requirements = db.Column(db.Text, nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    link = db.Column(db.String(500), nullable=True)
    format = db.Column(db.String(10), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    image_file = db.Column(db.String(255), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)

    def __repr__(self):
        return f'<EventEditRequest {self.id} event_id={self.event_id} status={self.status}>'
