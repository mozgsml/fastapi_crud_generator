# fastapi-crud-generator

[![Tests](https://github.com/mozgsml/fastapi_crud_generator/actions/workflows/tests.yml/badge.svg)](https://github.com/mozgsml/fastapi_crud_generator/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/fastapi-crud-generator)](https://pypi.org/project/fastapi-crud-generator/)
[![Python](https://img.shields.io/pypi/pyversions/fastapi-crud-generator)](https://pypi.org/project/fastapi-crud-generator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/mozgsml/fastapi_crud_generator/blob/main/LICENSE.txt)

Adds full CRUD routes to FastAPI without writing schemas, filters, or pagination by hand.
Everything is generated automatically from your ORM model.

## Three lines to a working API

```python
from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter

crud = CRUDCollection(orm_adapter=SQLModelAdapter(model=Article, get_session=get_session))
app.include_router(crud.get_router(prefix="/articles", tags=["articles"]))
```

That's enough for a complete set of endpoints:

| Method | URL | Description |
|---|---|---|
| `GET` | `/articles` | List with filtering, sorting, and pagination |
| `GET` | `/articles/{article_id}` | Get by ID |
| `POST` | `/articles` | Create |
| `PATCH` | `/articles/{article_id}` | Partial update |
| `DELETE` | `/articles/{article_id}` | Delete |

Request/response schemas, filters, sorting, and pagination are all derived
from the ORM model — no extra code needed.

## Installation

If SQLModel, SQLAlchemy, or Tortoise is already in your project:

```bash
pip install fastapi-crud-generator
```

To install an ORM together with the package:

```bash
pip install "fastapi-crud-generator[sqlmodel]"
pip install "fastapi-crud-generator[sqlalchemy]"
pip install "fastapi-crud-generator[tortoise]"
```

## What you get out of the box

- **Auto schemas** — public, create, and update schemas generated from the ORM model; no `ArticleCreate(BaseModel)` boilerplate
- **Filtering** — `?title=hello&published=true` with no extra code
- **Sorting** — `?sort=created_at:desc`
- **Pagination** — `?page=2&per_page=10`, response includes `count`, `page`, `data`
- **Nested resources** — `/threads/{thread_id}/posts/{post_id}` via `add_nested_collection`
- **SQLModel, SQLAlchemy, Tortoise ORM** support
- **Customizable** — replace any schema with your own, override any handler

## Next steps

[Getting Started](guide/getting-started.md) — full working example from scratch.
