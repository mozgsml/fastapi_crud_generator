# fastapi-crud-generator

CRUD route generator for FastAPI. Quickly adds standard endpoints (get one, get many, create, update, delete) to any ORM via an adapter.

## Installation

```bash
# from GitHub
pip install git+https://github.com/mozgsml/fastapi_crud_generator.git

# with SQLModel support
pip install "fastapi-crud-generator[sqlmodel] @ git+https://github.com/mozgsml/fastapi_crud_generator.git"

# via uv
uv add git+https://github.com/mozgsml/fastapi_crud_generator
```

## Quick start

```python
from fastapi import FastAPI
from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter  # if using SQLModel

app = FastAPI()

crud = CRUDCollection(
    orm_adapter=SQLModelAdapter(MyModel, get_session),
    public_schema=MyPublicSchema,
    create_schema=MyCreateSchema,
    update_schema=MyUpdateSchema,
)

app.include_router(crud.get_router(), prefix="/items", tags=["items"])
```

## CRUDCollection parameters

| Parameter | Description |
|---|---|
| `orm_adapter` | ORM adapter (required) |
| `public_schema` | Pydantic schema for reading |
| `public_list_schema` | Schema for list responses (defaults to `PaginatorPage[public_schema]`) |
| `create_schema` | Schema for creation |
| `update_schema` | Schema for updates |
| `pk_fields` | Pydantic model with primary key fields (defaults to `Id_UUID`) |
| `filter_schema` | Filter schema (auto-generated from `public_schema`) |
| `sort_schema` | Sort schema (auto-generated) |
| `include_schema` | Schema for including related data |

### Disabling individual routes

```python
crud = CRUDCollection(
    orm_adapter=...,
    public_schema=...,
    disable_delete=True,
    disable_create=True,
)
```

### FastAPI dependencies

```python
crud = CRUDCollection(
    orm_adapter=...,
    public_schema=...,
    dependencies=[Depends(require_auth)],            # for all routes
    get_many_dependencies=[Depends(require_admin)],  # GET / only
    create_dependencies=[Depends(require_admin)],
)
```

## Custom ORM adapter

Inherit from `ORMAdapterBase` and implement the required methods:

```python
from fastapi_crud_generator.orm.base import ORMAdapterBase

class MyAdapter(ORMAdapterBase):
    async def get_many_endpoint(self, ...): ...
    async def get_one_endpoint(self, ...): ...
    async def create_one_endpoint(self, ...): ...
    async def update_one_endpoint(self, ...): ...
    async def delete_one_endpoint(self, ...): ...
```
