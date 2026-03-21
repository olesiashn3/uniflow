from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional, URL
from app.models import User


class RegisterForm(FlaskForm):
    username = StringField('Імʼя користувача', validators=[
        DataRequired(message='Це поле обовʼязкове'),
        Length(min=3, max=64, message='Від 3 до 64 символів')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Це поле обовʼязкове'),
        Email(message='Введіть коректний email')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Це поле обовʼязкове'),
        Length(min=6, message='Мінімум 6 символів')
    ])
    password2 = PasswordField('Повторіть пароль', validators=[
        DataRequired(message='Це поле обовʼязкове'),
        EqualTo('password', message='Паролі не співпадають')
    ])
    submit = SubmitField('Зареєструватись')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Це імʼя вже зайняте')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Цей email вже зареєстрований')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message='Це поле обовʼязкове'),
        Email(message='Введіть коректний email')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Це поле обовʼязкове')
    ])
    submit = SubmitField('Увійти')


class EventForm(FlaskForm):
    title = StringField('Назва події', validators=[
        DataRequired(message='Це поле обовʼязкове'),
        Length(min=5, max=200, message='Від 5 до 200 символів')
    ])
    description = TextAreaField('Опис', validators=[
        DataRequired(message='Це поле обовʼязкове'),
        Length(min=20, message='Мінімум 20 символів')
    ])
    requirements = TextAreaField('Вимоги', validators=[Optional()])
    deadline = DateField('Дедлайн', validators=[Optional()])
    link = StringField('Посилання на офіційний сайт', validators=[
        Optional(),
        URL(message='Введіть коректне посилання')
    ])
    category_id = SelectField('Категорія', coerce=int)
    submit = SubmitField('Додати подію')