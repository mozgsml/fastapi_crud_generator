# fastapi-crud-generator

CRUD route generator for FastAPI. Adds standard endpoints (list, get, create, update, delete) to any ORM via an adapter — with nested resources, filtering, sorting, and pagination out of the box.

[![Tests](https://github.com/mozgsml/fastapi_crud_generator/actions/workflows/tests.yml/badge.svg)](https://github.com/mozgsml/fastapi_crud_generator/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/fastapi-crud-generator)](https://pypi.org/project/fastapi-crud-generator/)
[![Python](https://img.shields.io/pypi/pyversions/fastapi-crud-generator)](https://pypi.org/project/fastapi-crud-generator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.txt)

## Installation

```bash
pip install fastapi-crud-generator            # base (bring your own ORM)
pip install "fastapi-crud-generator[sqlmodel]"    # + SQLModel
pip install "fastapi-crud-generator[sqlalchemy]"  # + pure SQLAlchemy
pip install "fastapi-crud-generator[tortoise]"    # + Tortoise ORM
```

## Quick start

### SQLModel

```python
from fastapi import FastAPI
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter

app = FastAPI()

crud = CRUDCollection(orm_adapter=SQLModelAdapter(MyModel, get_session))
app.include_router(crud.get_router(prefix="/items"))
```

### SQLAlchemy (DeclarativeBase)

```python
from fastapi_crud_generator.orm.sqlalchemy import SQLAlchemyAdapter

crud = CRUDCollection(orm_adapter=SQLAlchemyAdapter(MyModel, get_session))
app.include_router(crud.get_router(prefix="/items"))
```

### Tortoise ORM

```python
from fastapi_crud_generator.orm.tortoise import TortoiseAdapter

crud = CRUDCollection(orm_adapter=TortoiseAdapter(model=MyModel))
app.include_router(crud.get_router(prefix="/items"))
```

## Nested resources

```python
post_crud = CRUDCollection(orm_adapter=SQLModelAdapter(Post, get_session))
thread_crud = CRUDCollection(orm_adapter=SQLModelAdapter(Thread, get_session))

thread_crud.add_nested_collection("/posts", post_crud)
app.include_router(thread_crud.get_router(prefix="/threads"))
# → GET/POST /threads/{thread_id}/posts
# → GET/PATCH/DELETE /threads/{thread_id}/posts/{post_id}
```

## CRUDCollection options

| Parameter | Description |
|---|---|
| `orm_adapter` | ORM adapter (required) |
| `public_schema` | Pydantic schema for reading |
| `create_schema` | Schema for creation |
| `update_schema` | Schema for updates |
| `pk_fields` | Primary key model (auto-detected) |
| `filter_schema` | Filter schema (auto-generated) |
| `sort_schema` | Sort schema (auto-generated) |
| `include_schema` | Schema for including related data |
| `disable_get_one` | Disable `GET /{id}` |
| `disable_get_many` | Disable `GET /` |
| `disable_create` | Disable `POST /` |
| `disable_update` | Disable `PATCH /{id}` |
| `disable_delete` | Disable `DELETE /{id}` |
| `dependencies` | FastAPI dependencies applied to all routes |

## Custom ORM adapter

```python
from fastapi_crud_generator.orm.base import ORMAdapterBase

class MyAdapter(ORMAdapterBase):
    async def get_one(self, pk_values, include_data, parent_refs): ...
    async def get_many(self, filter_data, sort_data, include_data, paginator, parent_refs): ...
    async def create_one(self, data, parent_refs): ...
    async def update_one(self, pk_values, data, parent_refs): ...
    async def delete_one(self, pk_values, parent_refs): ...
```

## License

MIT
