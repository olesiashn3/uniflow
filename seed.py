from app import create_app, db
from app.models import Category, User

app = create_app()

with app.app_context():
    # Категорії
    categories = [
        'Гранти',
        'Стажування',
        'Курси',
        'Хакатони',
        'Волонтерство',
        'Конференції',
        'Конкурси',
        'Обміни',
        'Інше'
    ]

    for name in categories:
        if not Category.query.filter_by(name=name).first():
            category = Category(name=name)
            db.session.add(category)

    # Адмін користувач
    if not User.query.filter_by(email='admin@uniflow.com').first():
        admin = User(
            username='admin',
            email='admin@uniflow.com',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)

    db.session.commit()
    print('Категорії та адмін додані!')