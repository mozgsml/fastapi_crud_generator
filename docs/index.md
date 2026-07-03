# fastapi-crud-generator

[![Tests](https://github.com/mozgsml/fastapi_crud_generator/actions/workflows/tests.yml/badge.svg)](https://github.com/mozgsml/fastapi_crud_generator/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/fastapi-crud-generator)](https://pypi.org/project/fastapi-crud-generator/)
[![Python](https://img.shields.io/pypi/pyversions/fastapi-crud-generator)](https://pypi.org/project/fastapi-crud-generator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/mozgsml/fastapi_crud_generator/blob/main/LICENSE.txt)

Подключает полноценный CRUD к FastAPI без написания схем, фильтров и пагинации вручную.
Схемы генерируются из ORM-модели автоматически.

## Три строки до работающего API

```python
from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter

crud = CRUDCollection(orm_adapter=SQLModelAdapter(model=Article, get_session=get_session))
app.include_router(crud.get_router(prefix="/articles", tags=["articles"]))
```

Этого достаточно для полного набора эндпоинтов:

| Метод | URL | Описание |
|---|---|---|
| `GET` | `/articles` | Список с фильтрацией, сортировкой и пагинацией |
| `GET` | `/articles/{article_id}` | Получить по ID |
| `POST` | `/articles` | Создать |
| `PATCH` | `/articles/{article_id}` | Частично обновить |
| `DELETE` | `/articles/{article_id}` | Удалить |

Схемы запросов и ответов, фильтры по всем полям, сортировка и постраничная
навигация — всё генерируется автоматически из ORM-модели. Ничего дополнительно
писать не нужно.

## Установка

Если SQLModel, SQLAlchemy или Tortoise уже есть в проекте — достаточно:

```bash
pip install fastapi-crud-generator
```

Если нужно установить ORM вместе с пакетом:

```bash
pip install "fastapi-crud-generator[sqlmodel]"
pip install "fastapi-crud-generator[sqlalchemy]"
pip install "fastapi-crud-generator[tortoise]"
```

## Что доступно из коробки

- **Автосхемы** — public, create, update генерируются из ORM-модели;
  никаких `class ArticleCreate(BaseModel): ...`
- **Фильтрация** — `?title=hello&status=published` без дополнительного кода
- **Сортировка** — `?sort=created_at:desc`
- **Пагинация** — `?page=2&per_page=10`, ответ содержит `count`, `page`, `data`
- **Вложенные ресурсы** — `/threads/{thread_id}/posts/{post_id}` через `add_nested_collection`
- **Поддержка SQLModel, SQLAlchemy, Tortoise ORM**
- **Кастомизация** — любую схему можно заменить своей, любой хендлер переопределить

## Быстрее начать

[Getting Started](guide/getting-started.md) — полный рабочий пример с нуля.
