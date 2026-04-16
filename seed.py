from app import create_app, db
from app.models import Category, User, Event, Company
from datetime import date, timedelta

app = create_app()

with app.app_context():
    # 1. ТОЧНІ КАТЕГОРІЇ З ТВОГО ДИЗАЙНУ
    category_names = [
        'IT та розробка', 'SMM та Маркетинг', 'Startups & Бізнес', 'UI/UX Дизайн',
        'Волонтерство', 'Геймдев (Gamedev)', 'Гранти', 'Еко-ініціативи',
        'Закордонні стажування', 'Інше', 'Конкурси', 'Конференції',
        'Креативні індустрії', 'Культура та Мистецтво', 'Курси',
        'Менеджмент та QA', 'Наука та гранти', 'Обміни', 'Стажування',
        'Студрада та активізм', 'Хакатони', 'Штучний інтелект (AI)'
    ]

    categories = {}
    for name in category_names:
        cat = Category.query.filter_by(name=name).first()
        if not cat:
            cat = Category(name=name)
            db.session.add(cat)
            db.session.commit()
        categories[name] = cat

    # 2. АДМІН
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User.query.first()  # Якщо адміна нема, беремо першого юзера

    # 3. 5 ОРГАНІЗАЦІЙ
    companies_data = [
        {"name": "CloudNova Hub",
         "description": "Провайдер інноваційних хмарних рішень. Спеціалізуємось на IaaS, PaaS та SaaS інфраструктурах на базі Google Cloud Platform.",
         "verified": True},
        {"name": "Lviv Content Creators",
         "description": "Креативна агенція повного циклу. Створюємо брендовий відеоконтент, розробляємо SMM-стратегії.",
         "verified": True},
        {"name": "DeskSpace Solutions",
         "description": "Продуктова компанія, що розробляє системи бронювання коворкінгів та гнучких робочих місць.",
         "verified": False},
        {"name": "PixelForge Studio",
         "description": "Інді-студія розробки ігор. Наш фокус — піксель-арт, глибокий лор та атмосферні 2D проекти.",
         "verified": False},
        {"name": "FrankoTech Campus",
         "description": "Студентський технологічний хаб при університеті. Організовуємо наукові форуми, лекції з архітектури ПЗ.",
         "verified": True}
    ]

    new_companies = []
    for c_data in companies_data:
        comp = Company.query.filter_by(name=c_data["name"]).first()
        if not comp:
            comp = Company(name=c_data["name"], description=c_data["description"], is_verified=c_data["verified"])
            db.session.add(comp)
            db.session.commit()
        new_companies.append(comp)

    # 4. 18 ПОДІЙ ІЗ ПРАВИЛЬНИМИ КАТЕГОРІЯМИ
    events_data = [
        {
            "title": "Курс: Архітектурні патерни в розробці ПЗ",
            "category": "IT та розробка",
            "format": "online", "city": "Онлайн", "deadline_days": 10, "company_idx": 4,
            "desc": "Глибоке занурення в дизайн ПЗ. Розберемо на практиці Factory Method, Prototype, Singleton та Builder. Будуємо масштабовані системи.",
            "reqs": "Студенти 3 курсу і старше. Базові знання ООП."
        },
        {
            "title": "SMM-менеджер / Content Maker (Стажування)",
            "category": "SMM та Маркетинг",
            "format": "offline", "city": "Львів", "deadline_days": 5, "company_idx": 1,
            "desc": "Шукаємо креативного фахівця. Обов'язки: створення контент-планів, монтаж у CapCut та DaVinci Resolve, студійна фотозйомка.",
            "reqs": "Розуміння алгоритмів соцмереж, наявність портфоліо."
        },
        {
            "title": "Bootcamp: Google Cloud Platform",
            "category": "Курси",
            "format": "online", "city": "Онлайн", "deadline_days": 14, "company_idx": 0,
            "desc": "Підготовка до сертифікації GCP. Вивчимо налаштування VPC, розгортання віртуальних машин та роботу з Deployment Manager.",
            "reqs": "Розуміння IaaS, PaaS, SaaS."
        },
        {
            "title": "Хакатон: Backend для DeskSpace",
            "category": "Хакатони",
            "format": "offline", "city": "Львів", "deadline_days": 21, "company_idx": 2,
            "desc": "Створіть ядро системи бронювання коворкінгів, використовуючи мікросервісну архітектуру. Переможці отримають фінансування.",
            "reqs": "Команди до 5 осіб."
        },
        {
            "title": "Конкурс 2D персонажів та лору",
            "category": "Геймдев (Gamedev)",
            "format": "online", "city": "Онлайн", "deadline_days": 30, "company_idx": 3,
            "desc": "Створюєш піксель-арт? Надішли концепт свого ігрового персонажа разом з лором. Переможці долучаться до нашого нового проекту.",
            "reqs": "Скетчі, фінальний арт та текстовий опис."
        },
        {
            "title": "Грант на студійне обладнання",
            "category": "Гранти",
            "format": "online", "city": "Онлайн", "deadline_days": 45, "company_idx": 1,
            "desc": "Надаємо фінансування на техніку (Sony ZV-E10, об'єктиви, освітлення) для розвитку вашого SMM чи відео-бренду.",
            "reqs": "Детальний бізнес-план."
        },
        {
            "title": "AI в SMM: Від ChatGPT до Midjourney",
            "category": "Штучний інтелект (AI)",
            "format": "online", "city": "Онлайн", "deadline_days": 2, "company_idx": 1,
            "desc": "Воркшоп про використання штучного інтелекту для генерації контент-планів, текстів та візуалу для брендів.",
            "reqs": "Базовий досвід роботи з нейромережами."
        },
        {
            "title": "Лекція: Основи UI/UX для розробників",
            "category": "UI/UX Дизайн",
            "format": "offline", "city": "Київ", "deadline_days": 8, "company_idx": 4,
            "desc": "Як зробити інтерфейс зручним, якщо ти бекенд-розробник. Розбираємо основи Figma та правила юзабіліті.",
            "reqs": "Бажання розширити свій стек."
        },
        {
            "title": "Стажування: Software Analyst & PM",
            "category": "Менеджмент та QA",
            "format": "online", "city": "Онлайн", "deadline_days": 3, "company_idx": 2,
            "desc": "Шукаємо аналітика та проектного менеджера для студентських SaaS-проектів. Ведення документації, організація спрінтів.",
            "reqs": "Розуміння життєвого циклу SDLC."
        },
        {
            "title": "GameDev Volunteer на піксель-фест",
            "category": "Волонтерство",
            "format": "offline", "city": "Київ", "deadline_days": 7, "company_idx": 3,
            "desc": "Допоможіть з навігацією, супроводом інді-розробників та організацією зон тестування ігор на фестивалі.",
            "reqs": "Відповідальність, любов до відеоігор."
        },
        {
            "title": "Обмін: IT-технології у Варшаві",
            "category": "Обміни",
            "format": "offline", "city": "Варшава", "deadline_days": 60, "company_idx": None,
            "desc": "Семестрова програма обміну. Вивчайте хмарні технології та архітектуру у провідних технічних ВНЗ Польщі.",
            "reqs": "Англійська В2+, середній бал від 4.5."
        },
        {
            "title": "Акселератор студентських стартапів",
            "category": "Startups & Бізнес",
            "format": "offline", "city": "Львів", "deadline_days": 25, "company_idx": 4,
            "desc": "Маєте ідею SaaS-продукту? Приходьте на акселератор, щоб навчитися будувати бізнес-модель та залучати інвестиції.",
            "reqs": "Наявність прототипу або MVP."
        },
        {
            "title": "Еко-ініціатива: Greener Campus",
            "category": "Еко-ініціативи",
            "format": "offline", "city": "Львів", "deadline_days": 12, "company_idx": None,
            "desc": "Долучайтесь до розробки системи розумного сортування сміття та енергозбереження в університеті з використанням IoT.",
            "reqs": "Бути студентом місцевого ВНЗ."
        },
        {
            "title": "Науковий форум: Інновації в IT",
            "category": "Наука та гранти",
            "format": "offline", "city": "Львів", "deadline_days": 12, "company_idx": 4,
            "desc": "Презентуй тези про хмарні інструменти чи архітектуру ПЗ перед експертами.",
            "reqs": "Презентація на 5-7 слайдів."
        },
        {
            "title": "Закордонне стажування: Cloud Engineer",
            "category": "Закордонні стажування",
            "format": "offline", "city": "Берлін", "deadline_days": 90, "company_idx": 0,
            "desc": "Літнє стажування в офісі CloudNova у Берліні. Практика з великими даними та інфраструктурою GCP.",
            "reqs": "Рівень English Advanced, знання Cloud Computing."
        },
        {
            "title": "Конференція кріейторів",
            "category": "Креативні індустрії",
            "format": "offline", "city": "Київ", "deadline_days": 15, "company_idx": 1,
            "desc": "Найбільший зліт відеомейкерів, фотографів та SMMників. Обмін досвідом, розбір кейсів та нетворкінг.",
            "reqs": "Для всіх бажаючих."
        },
        {
            "title": "Студрада: Вибори голови IT-комітету",
            "category": "Студрада та активізм",
            "format": "offline", "city": "Львів", "deadline_days": 4, "company_idx": None,
            "desc": "Шукаємо лідера, який буде організовувати мітапи, хакатони та воркшопи для студентів нашого факультету.",
            "reqs": "Висока мотивація, лідерські якості."
        },
        {
            "title": "Виставка цифрового мистецтва",
            "category": "Культура та Мистецтво",
            "format": "offline", "city": "Одеса", "deadline_days": 22, "company_idx": 3,
            "desc": "Презентація кращих робіт 2D-художників, аніматорів та піксель-артистів. Шукаємо нові таланти для ігрової індустрії.",
            "reqs": "Вхід вільний."
        }
    ]

    events_added = 0
    for data in events_data:
        existing_event = Event.query.filter_by(title=data["title"]).first()
        if not existing_event:
            comp = new_companies[data["company_idx"]] if data["company_idx"] is not None else None

            event = Event(
                title=data["title"],
                description=data["desc"],
                requirements=data["reqs"],
                format=data["format"],
                city=data["city"],
                link="https://uniflow.com/join",
                deadline=date.today() + timedelta(days=data["deadline_days"]),
                category_id=categories[data["category"]].id,
                company_id=comp.id if comp else None,
                author_id=admin.id if admin else 1,
                status='approved',
                image_file='default.jpg'
            )
            db.session.add(event)
            events_added += 1

    db.session.commit()
    print(f'Готово! Категорії синхронізовано. Додано {events_added} нових подій у стрічку.')