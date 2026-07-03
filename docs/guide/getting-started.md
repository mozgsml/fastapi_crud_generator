# Getting Started

Полный пример с нуля на SQLModel. Для SQLAlchemy и Tortoise принцип тот же — см. [ORM Adapters](orm-adapters.md).

## Установка

```bash
pip install "fastapi-crud-generator[sqlmodel]"
pip install aiosqlite  # или asyncpg для PostgreSQL
```

## Модель

```python
from sqlmodel import Field, SQLModel

class Article(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    content: str
    published: bool = False
```

Никаких дополнительных Pydantic-схем писать не нужно — они генерируются автоматически.

## Сессия

```python
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from collections.abc import AsyncGenerator

engine = create_async_engine("sqlite+aiosqlite:///db.sqlite3")

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session
```

## Подключение CRUD

```python
from fastapi import FastAPI
from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter

app = FastAPI()

crud = CRUDCollection(
    orm_adapter=SQLModelAdapter(model=Article, get_session=get_session),
)
app.include_router(crud.get_router(prefix="/articles", tags=["articles"]))
```

## Что получается

Пять эндпоинтов с полной документацией в `/docs`:

| Метод | URL | Тело запроса | Ответ |
|---|---|---|---|
| `GET` | `/articles` | — | `{ page, per_page, count, data: [...] }` |
| `GET` | `/articles/{article_id}` | — | объект статьи |
| `POST` | `/articles` | `{ title, content, published }` | созданный объект |
| `PATCH` | `/articles/{article_id}` | любые поля (все опциональны) | `null` |
| `DELETE` | `/articles/{article_id}` | — | удалённый объект |

### Схемы

Адаптер сам решает, какие поля включить в каждую схему:

- **public** (GET-ответы) — все поля модели, включая `id`
- **create** (POST) — все поля кроме `id` (первичный ключ генерирует БД)
- **update** (PATCH) — те же поля что в create, но все опциональны

### Фильтрация

```
GET /articles?published=true
GET /articles?title=hello
```

### Сортировка

```
GET /articles?sort=title
GET /articles?sort=title:desc
GET /articles?sort=title:asc&sort=published:desc
```

### Пагинация

```
GET /articles?page=2&per_page=5
```

```json
{
  "page": 2,
  "per_page": 5,
  "count": 42,
  "data": [...]
}
```

## Дальше

- [Schema Generation](schema-generation.md) — как управлять полями схем
- [Filtering & Sorting](filtering-sorting.md) — кастомные фильтры
- [Nested Resources](nested-resources.md) — вложенные маршруты
