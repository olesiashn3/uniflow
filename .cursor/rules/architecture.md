# Архітектура UniFlow (In-Memory та шари абстракцій)

## Мета
Платформа відокремлює **доступ до даних**, **варіанти сортування** та **побічні ефекти (сповіщення)** від HTTP-роутів, щоб спростити тестування та заміну реалізацій.

## Репозиторії подій (`app/repositories/`)

### Інтерфейс
- **`IEventRepository`** — абстрактний контракт методу `build_public_events_query(...)`.

### Реалізації
- **`SqlAlchemyEventRepository`** — продакшен-шлях: фільтри (статус `approved`, дедлайн, пошук, категорія, формат, місто, стрічка `feed`) та делегування **стратегії сортування** до SQLAlchemy `Query` з `.paginate()`.
- **`InMemoryEventRepository`** — зберігання подій у **списку об’єктів** (duck typing полів як у `Event`). Призначення: **ізольовані юніт-тести** без MySQL.
- **`InMemoryPublicEventsResult`** + **`ListPagination`** — імітація пагінації Flask-SQLAlchemy (`items`, `total`, `pages`, `has_prev` / `has_next`, `prev_num` / `next_num`, `iter_pages`), щоб шаблони та роути не розрізняли джерело даних за API вибірки.

## Стратегії сортування (`app/strategies/`)

- **`EventSortStrategy`** — спільний контракт для:
  - `apply_sqlalchemy(query)` — додати порядок / фільтр на рівні БД;
  - `apply_in_memory(events)` — повернути новий відсортований список.
- **`SortByNewest`**, **`SortByDeadline`** — конкретні стратегії.
- **`get_event_sort_strategy(sort_key)`** — фабрика; невідомі ключі відкочуються до сортування «за новизною».

## Observer для організацій (`app/observers/`)

- **`OrganizationApprovalSubject`** — зберігає спостерігачів, метод `notify(ctx)`.
- **`OrganizationApprovedContext`** — immutable контекст (`requester_id`, `company_name`).
- **`OrganizationApprovedNotificationObserver`** — викликає сервіс сповіщень після схвалення запиту на організацію.
- Роут адмінки лише викликає **`notify_organization_request_approved(...)`** після commit; логіка «що саме зробити після схвалення» розширюється новими спостерігачами без зміни маршруту.

## Принципи SOLID (коротко)
- **D (DIP):** залежність стрічки подій від `IEventRepository`, а не від конкретного ORM-запиту в роуті.
- **OCP:** нові стратегії сортування або observers додаються без модифікації існуючих умов `if/else` у роутах (через реєстр / attach).

## Де читати код
- `app/repositories/event_repository.py`
- `app/strategies/event_sort.py`
- `app/observers/organization_approval.py`
- `app/services/events_service.py` — фасад `build_events_query(..., repository=...)`.
