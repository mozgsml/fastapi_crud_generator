# ORM Adapters

Адаптер связывает конкретный ORM с `CRUDCollection`. Он отвечает за генерацию схем
и выполнение запросов к базе данных.

## SQLModel

```python
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter

adapter = SQLModelAdapter(
    model=Article,
    get_session=get_session,  # async generator → AsyncSession
)
```

`get_session` — асинхронный генератор, который возвращает `sqlmodel.ext.asyncio.session.AsyncSession`.
Стандартный паттерн с FastAPI:

```python
from collections.abc import AsyncGenerator
from sqlmodel.ext.asyncio.session import AsyncSession

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session
```

## SQLAlchemy (DeclarativeBase)

Работает с `DeclarativeBase`-моделями напрямую, без SQLModel.

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from fastapi_crud_generator.orm.sqlalchemy import SQLAlchemyAdapter

class Base(DeclarativeBase):
    pass

class Article(Base):
    __tablename__ = "article"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    content: Mapped[str]
    published: Mapped[bool] = mapped_column(default=False)

adapter = SQLAlchemyAdapter(
    model=Article,
    get_session=get_session,  # async generator → AsyncSession
)
```

`get_session` возвращает `sqlalchemy.ext.asyncio.AsyncSession`.

## Tortoise ORM

Tortoise управляет соединениями глобально, поэтому `get_session` не нужен.

```python
from tortoise import fields
from tortoise.models import Model
from fastapi_crud_generator.orm.tortoise import TortoiseAdapter

class Article(Model):
    id = fields.IntField(primary_key=True)
    title = fields.CharField(max_length=200)
    content = fields.TextField()
    published = fields.BooleanField(default=False)

    class Meta:
        table = "article"

adapter = TortoiseAdapter(model=Article)
```

Инициализацию Tortoise делайте при старте приложения через lifespan:

```python
from contextlib import asynccontextmanager
from tortoise import Tortoise

@asynccontextmanager
async def lifespan(app):
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["myapp.models"]},
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()

app = FastAPI(lifespan=lifespan)
```

## Сравнение адаптеров

| | SQLModel | SQLAlchemy | Tortoise |
|---|---|---|---|
| Требует `get_session` | да | да | нет |
| Поддержка composite PK | да | да | нет (ограничение Tortoise) |
| `crud_config` на модели | да | нет | нет |
| Схемы из | `model_fields` | `mapped_column` | `pydantic_model_creator` |
