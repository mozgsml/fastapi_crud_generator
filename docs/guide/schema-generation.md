# Schema Generation

Схемы для запросов и ответов генерируются автоматически из ORM-модели.
Писать `ArticleCreate`, `ArticleUpdate`, `ArticlePublic` вручную не нужно.

## Что генерируется

Для модели:

```python
class Article(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    content: str
    published: bool = False
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime, server_default=func.now()),
    )
```

Адаптер автоматически строит три схемы:

| Схема | Поля | Используется в |
|---|---|---|
| **public** | `id`, `title`, `content`, `published`, `created_at` | GET-ответы |
| **create** | `title`, `content`, `published` | POST-тело |
| **update** | `title?`, `content?`, `published?` | PATCH-тело (все опциональны) |

`id` исключается из create/update — он генерируется базой.
`created_at` тоже исключается — у него `server_default`, значит БД проставляет значение сама.

## Управление полями через `crud_config`

Если нужно задать другие наборы полей — добавьте `crud_config` прямо на модель.
Адаптер подхватит его автоматически.

```python
from typing import ClassVar
from fastapi_crud_generator.config import CRUDConfigDict

class Article(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    content: str
    summary: str | None = None
    internal_notes: str | None = None  # не должно попадать в API

    crud_config: ClassVar[CRUDConfigDict] = CRUDConfigDict(
        public_fields={"id", "title", "summary"},
        create_fields={"title", "content", "summary"},
        update_fields={"title", "content", "summary"},
    )
```

!!! note
    `crud_config` нужно аннотировать как `ClassVar` — иначе ORM воспримет его как поле таблицы.

Поддерживается только в SQLModel-адаптере.

## `base_fields` — общие поля для всех схем

Если несколько схем разделяют одинаковый набор полей, вынесите их в `base_fields`:

```python
crud_config: ClassVar[CRUDConfigDict] = CRUDConfigDict(
    base_fields={"title", "content"},
    public_fields={"id", "published"},    # → id, published, title, content
    create_fields={"category_id"},        # → category_id, title, content
)
```

`base_fields` добавляется к каждому явно заданному набору.

## Кастомная схема вместо автогенерации

Любую схему можно заменить своей — просто передайте её в `CRUDCollection`.
Остальные схемы при этом продолжат генерироваться автоматически.

```python
class ArticleCreate(BaseModel):
    title: str
    content: str
    author_id: int  # поле, которого нет в ORM-модели

crud = CRUDCollection(
    orm_adapter=adapter,
    create_schema=ArticleCreate,  # только эта схема задана вручную
)
```

## Управление полями через аргументы адаптера

Можно передать поля напрямую при создании `CRUDCollection`:

```python
crud = CRUDCollection(
    orm_adapter=adapter,
    public_fields={"id", "title"},
    create_fields={"title", "content"},
)
```

Это удобно когда одна модель используется в нескольких `CRUDCollection` с разными наборами полей.
