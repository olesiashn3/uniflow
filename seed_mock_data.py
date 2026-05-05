from __future__ import annotations

from datetime import date, datetime

from app import create_app, db
from app.models import Category, Company, Event, NewsPost, User


def get_or_create_company(name: str, **kwargs) -> Company:
    c = Company.query.filter_by(name=name).first()
    if c:
        return c
    c = Company(name=name, **kwargs)
    db.session.add(c)
    db.session.commit()
    return c


def get_or_create_user(username: str, email: str, password: str, **kwargs) -> User:
    u = User.query.filter_by(email=email).first()
    if u:
        return u
    u = User(username=username, email=email, **kwargs)
    u.set_password(password)
    u.onboarding_done = True
    db.session.add(u)
    db.session.commit()
    return u


def get_or_create_category(name: str) -> Category:
    c = Category.query.filter_by(name=name).first()
    if c:
        return c
    c = Category(name=name)
    db.session.add(c)
    db.session.commit()
    return c


def ensure_news_post(company: Company, title: str, body: str, created_at: datetime) -> NewsPost:
    existing = NewsPost.query.filter_by(company_id=company.id, title=title).first()
    if existing:
        return existing
    p = NewsPost(company_id=company.id, title=title, body=body, created_at=created_at)
    db.session.add(p)
    db.session.commit()
    return p


def ensure_event(
    *,
    author: User,
    company: Company | None,
    category: Category,
    title: str,
    description: str,
    requirements: str | None,
    deadline: date,
    link: str | None,
    format_: str | None,
    city: str | None,
    status: str = "approved",
) -> Event:
    existing = Event.query.filter_by(author_id=author.id, title=title).first()
    if existing:
        return existing

    e = Event(
        title=title,
        description=description,
        requirements=requirements,
        deadline=deadline,
        link=link,
        format=format_ or None,
        city=city or None,
        image_file=None,
        status=status,
        author_id=author.id,
        category_id=category.id,
        company_id=(company.id if company else None),
        created_at=datetime.utcnow(),
    )
    db.session.add(e)
    db.session.commit()
    return e


def main() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()

        # Categories (minimal set; extend freely)
        cat_it = get_or_create_category("IT")
        cat_design = get_or_create_category("Дизайн")
        cat_business = get_or_create_category("Бізнес")
        cat_science = get_or_create_category("Наука")

        # Companies
        c1 = get_or_create_company(
            "TechNova",
            description="Продуктова компанія з фокусом на AI та data-driven рішення.",
            website="https://technova.example",
            logo_file=None,
            is_verified=True,
        )
        c2 = get_or_create_company(
            "DesignCraft",
            description="Студія дизайну та брендингу для стартапів і edtech.",
            website="https://designcraft.example",
            logo_file=None,
            is_verified=True,
        )
        c3 = get_or_create_company(
            "UniCommunity",
            description="Спільнота, яка робить події для студентів у різних містах.",
            website="https://unicommunity.example",
            logo_file=None,
            is_verified=False,
        )

        # Users
        alice = get_or_create_user("alice", "alice@example.com", "password123")
        bob = get_or_create_user("bob", "bob@example.com", "password123")
        org_rep_1 = get_or_create_user("technova_hr", "hr@technova.example", "password123", company_id=c1.id)
        org_rep_2 = get_or_create_user("designcraft", "hello@designcraft.example", "password123", company_id=c2.id)

        # Subscriptions so "Новини" section is not empty for demo users
        if c1 not in alice.subscribed_companies:
            alice.subscribed_companies.append(c1)
        if c2 not in alice.subscribed_companies:
            alice.subscribed_companies.append(c2)
        if c1 not in bob.subscribed_companies:
            bob.subscribed_companies.append(c1)
        db.session.commit()

        # News posts (dates are arbitrary, keep them recent)
        ensure_news_post(
            c1,
            "Відкрито набір на літню інтернатуру 2026",
            "Запрошуємо студентів 2–5 курсів. Формат: гібрид. Потрібні базові знання Python/SQL. Дедлайн подачі заявок — див. у відповідній події.",
            created_at=datetime(2026, 5, 1, 12, 0, 0),
        )
        ensure_news_post(
            c1,
            "Q&A: як ми відбираємо кандидатів",
            "Зібрали найчастіші питання про відбір, тестові та співбесіди. Якщо маєш питання — пиши в секцію питань під подією.",
            created_at=datetime(2026, 5, 3, 18, 30, 0),
        )
        ensure_news_post(
            c2,
            "Менторська програма для дизайнерів",
            "Запускаємо 6-тижневу менторську програму. Портфоліо буде плюсом, але не обовʼязково — головне мотивація.",
            created_at=datetime(2026, 5, 2, 10, 15, 0),
        )

        # Events with deadlines AFTER May (so they stay visible through the end of submission)
        ensure_event(
            author=org_rep_1,
            company=c1,
            category=cat_it,
            title="Internship: Data Analyst (Summer 2026)",
            description="Оплачуване стажування з реальними задачами, ментором і фінальним демо-днем.",
            requirements="Базовий SQL, аналітичне мислення, бажано Python.",
            deadline=date(2026, 6, 30),
            link="https://technova.example/internship",
            format_="online",
            city=None,
            status="approved",
        )
        ensure_event(
            author=org_rep_2,
            company=c2,
            category=cat_design,
            title="Design Challenge: UX для студентського застосунку",
            description="Практичний челендж з фідбеком від менторів і можливістю потрапити на стажування.",
            requirements="Figma, базові UX принципи. Досвід — не обовʼязково.",
            deadline=date(2026, 7, 15),
            link="https://designcraft.example/challenge",
            format_="online",
            city=None,
            status="approved",
        )
        ensure_event(
            author=alice,
            company=None,
            category=cat_business,
            title="Meetup: як зібрати CV/LinkedIn під стажування",
            description="Неформальна подія від студентів для студентів — ділимось прикладами, інструментами і помилками.",
            requirements=None,
            deadline=date(2026, 6, 20),
            link=None,
            format_="offline",
            city="Львів",
            status="approved",
        )
        ensure_event(
            author=bob,
            company=None,
            category=cat_science,
            title="Відкритий клуб: основи ML для початківців",
            description="4 зустрічі з практикою. Розберемо базові моделі і підготуємо міні-проєкт.",
            requirements="Базовий Python.",
            deadline=date(2026, 6, 10),
            link="https://unicommunity.example/ml-club",
            format_="online",
            city=None,
            status="approved",
        )

        print("Mock data seeded. Demo users: alice@example.com / bob@example.com (password123)")


if __name__ == "__main__":
    main()

