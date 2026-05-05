from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, DateField, HiddenField
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

    # Залишаємо URL, але додаємо підказку в placeholder (в HTML)
    link = StringField('Посилання (Реєстрація / Деталі)', validators=[
        Optional(),
        URL(message='Введіть коректне посилання (почніть з http:// або https://)')
    ])

    format = SelectField('Формат', choices=[
        ('', 'Не вказано'),
        ('online', 'Онлайн'),
        ('offline', 'Офлайн')
    ], validators=[Optional()])

    city = StringField('Місто', validators=[
        Optional(),
        Length(max=100)
    ])

    image = FileField('Обкладинка події (банер)', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Дозволені лише зображення (JPG, PNG)')
    ])

    category_id = SelectField('Категорія', coerce=int)

    # ДОДАНО: Приховане поле або список для вибору компанії
    # Якщо юзер має компанію, ми заповнимо цей список у маршруті
    company_id = SelectField('Публікувати від імені', coerce=int, validators=[Optional()])

    submit = SubmitField('Опублікувати')


class CompanyForm(FlaskForm):
    name = StringField('Назва організації', validators=[
        DataRequired(message='Це поле обовʼязкове'),
        Length(min=2, max=100, message='Від 2 до 100 символів')
    ])
    description = TextAreaField('Опис організації', validators=[Optional()])
    website = StringField('Вебсайт', validators=[
        Optional(),
        URL(message='Введіть коректне посилання')
    ])
    logo = FileField('Логотип', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Тільки зображення!')
    ])
    submit = SubmitField('Створити організацію')


class AssignCompanyForm(FlaskForm):
    username = StringField('Імʼя користувача', validators=[
        DataRequired(message='Це поле обовʼязкове')
    ])
    company_id = SelectField('Організація', coerce=int)
    submit = SubmitField('Прив\'язати')


class NewsPostForm(FlaskForm):
    title = StringField('Заголовок', validators=[
        DataRequired(message='Це поле обовʼязкове'),
        Length(min=4, max=200, message='Від 4 до 200 символів')
    ])
    body = TextAreaField('Текст допису', validators=[
        DataRequired(message='Це поле обовʼязкове'),
        Length(min=20, message='Мінімум 20 символів')
    ])
    image = FileField('Зображення (опціонально)', validators=[
        Optional(),
        FileAllowed(['jpg', 'png', 'jpeg', 'webp'], 'Дозволені лише зображення (JPG, PNG, WEBP)')
    ])
    submit = SubmitField('Опублікувати')


class OrganizationRequestForm(FlaskForm):
    company_name = StringField('Назва компанії / організації', validators=[
        DataRequired(message='Це поле обовʼязкове'),
        Length(min=2, max=140, message='Від 2 до 140 символів')
    ])
    social_link = StringField('Посилання на соцмережу / сайт', validators=[
        Optional(),
        URL(message='Введіть коректне посилання (почніть з http:// або https://)')
    ])
    contact_email = StringField('Контактна пошта', validators=[
        DataRequired(message='Це поле обовʼязкове'),
        Email(message='Введіть коректний email')
    ])
    comment = TextAreaField('Коментар для адміністратора', validators=[
        Optional(),
        Length(max=2000, message='Максимум 2000 символів')
    ])
    submit = SubmitField('Надіслати на розгляд')


class UserProfileForm(FlaskForm):
    full_name = StringField('Імʼя та прізвище', validators=[Optional(), Length(max=140)])
    headline = StringField('Заголовок', validators=[Optional(), Length(max=160)])
    bio = TextAreaField('Про себе', validators=[Optional(), Length(max=4000)])
    education = StringField('Навчання', validators=[Optional(), Length(max=200)])
    work = StringField('Робота', validators=[Optional(), Length(max=200)])
    avatar = FileField('Аватар', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Тільки зображення!')
    ])
    submit = SubmitField('Зберегти профіль')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Поточний пароль', validators=[DataRequired(message='Це поле обовʼязкове')])
    new_password = PasswordField('Новий пароль', validators=[
        DataRequired(message='Це поле обовʼязкове'),
        Length(min=6, message='Мінімум 6 символів')
    ])
    new_password2 = PasswordField('Повторіть новий пароль', validators=[
        DataRequired(message='Це поле обовʼязкове'),
        EqualTo('new_password', message='Паролі не співпадають')
    ])
    submit = SubmitField('Змінити пароль')


class EventEditForm(FlaskForm):
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
    link = StringField('Посилання (Реєстрація / Деталі)', validators=[
        Optional(),
        URL(message='Введіть коректне посилання (почніть з http:// або https://)')
    ])
    format = SelectField('Формат', choices=[
        ('', 'Не вказано'),
        ('online', 'Онлайн'),
        ('offline', 'Офлайн')
    ], validators=[Optional()])
    city = StringField('Місто', validators=[Optional(), Length(max=100)])
    image = FileField('Обкладинка події (банер)', validators=[
        Optional(),
        FileAllowed(['jpg', 'png', 'jpeg', 'webp'], 'Дозволені лише зображення')
    ])
    category_id = SelectField('Категорія', coerce=int)
    company_id = SelectField('Публікувати від імені', coerce=int, validators=[Optional()])
    submit = SubmitField('Надіслати на перевірку')

