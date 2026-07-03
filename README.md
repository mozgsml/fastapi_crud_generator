# fastapi-crud-generator

[![Tests](https://github.com/mozgsml/fastapi_crud_generator/actions/workflows/tests.yml/badge.svg)](https://github.com/mozgsml/fastapi_crud_generator/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/fastapi-crud-generator)](https://pypi.org/project/fastapi-crud-generator/)
[![Python](https://img.shields.io/pypi/pyversions/fastapi-crud-generator)](https://pypi.org/project/fastapi-crud-generator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.txt)

CRUD route generator for FastAPI. Point it at an ORM model and get a full set of
endpoints — with filtering, sorting, pagination, and nested resources — without writing
a single Pydantic schema by hand.

Works with **SQLModel**, **SQLAlchemy**, and **Tortoise ORM**.

## What it does

- **Auto schemas** — public, create, and update schemas are derived from the ORM model automatically
- **Filtering** — every scalar field becomes a query parameter: `?status=published&author_id=5`
- **Sorting** — `?sort=created_at:desc` or multiple: `?sort=published:desc&sort=title:asc`
- **Pagination** — `?page=2&per_page=20`, response always includes total `count`
- **Nested resources** — `/threads/{thread_id}/posts/{post_id}` in three lines
- **Related data** — fetch relations in a single request via `?include=author,tags`
- **Customizable** — disable any endpoint, override any handler, replace any schema

## Quick start

```python
from fastapi import FastAPI
from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter

app = FastAPI()

crud = CRUDCollection(orm_adapter=SQLModelAdapter(model=Article, get_session=get_session))
app.include_router(crud.get_router(prefix="/articles", tags=["articles"]))
```

This registers five endpoints:

```
GET    /articles               # list: filtering, sorting, pagination
GET    /articles/{article_id}  # get one
POST   /articles               # create
PATCH  /articles/{article_id}  # partial update
DELETE /articles/{article_id}  # delete
```

Request and response schemas are generated from the `Article` model automatically —
no `ArticleCreate`, `ArticleUpdate`, or `ArticlePublic` classes needed.

## Nested resources

```python
thread_crud = CRUDCollection(orm_adapter=SQLModelAdapter(model=Thread, get_session=get_session))
post_crud   = CRUDCollection(orm_adapter=SQLModelAdapter(model=Post,   get_session=get_session))

thread_crud.add_nested_collection("/posts", post_crud)
app.include_router(thread_crud.get_router(prefix="/threads"))
```

This gives you the full hierarchy:

```
GET    /threads
GET    /threads/{thread_id}
POST   /threads
PATCH  /threads/{thread_id}
DELETE /threads/{thread_id}

GET    /threads/{thread_id}/posts
GET    /threads/{thread_id}/posts/{post_id}
POST   /threads/{thread_id}/posts
PATCH  /threads/{thread_id}/posts/{post_id}
DELETE /threads/{thread_id}/posts/{post_id}
```

Filtering, sorting, and pagination work on nested routes too. Post queries are
automatically scoped to the parent thread.

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

## Documentation

**[mozgsml.github.io/fastapi_crud_generator](https://mozgsml.github.io/fastapi_crud_generator)**

## License

MIT
