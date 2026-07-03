# ORM Adapters

An adapter connects a specific ORM to `CRUDCollection`. It handles schema generation
and executes database queries.

## SQLModel

```python
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter

adapter = SQLModelAdapter(
    model=Article,
    get_session=get_session,  # async generator → AsyncSession
)
```

`get_session` is an async generator that yields a `sqlmodel.ext.asyncio.session.AsyncSession`.
Standard FastAPI pattern:

```python
from collections.abc import AsyncGenerator
from sqlmodel.ext.asyncio.session import AsyncSession

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session
```

## SQLAlchemy (DeclarativeBase)

Works directly with `DeclarativeBase` models, without SQLModel.

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

`get_session` yields a `sqlalchemy.ext.asyncio.AsyncSession`.

## Tortoise ORM

Tortoise manages connections globally, so no `get_session` is needed.

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

Initialize Tortoise at application startup via lifespan:

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

## Comparison

| | SQLModel | SQLAlchemy | Tortoise |
|---|---|---|---|
| Requires `get_session` | yes | yes | no |
| Composite PK support | yes | yes | no (Tortoise limitation) |
| `crud_config` on model | yes | no | no |
| Schemas built from | `model_fields` | `mapped_column` | `pydantic_model_creator` |
