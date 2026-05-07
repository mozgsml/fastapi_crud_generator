# fastapi-crud-generator

CRUD route generator for FastAPI. Quickly adds standard endpoints
(get one, get many, create, update, delete) to any ORM via an adapter.

## Installation

```bash
pip install git+https://github.com/mozgsml/fastapi_crud_generator.git

# with SQLModel support
pip install "fastapi-crud-generator[sqlmodel] @ git+https://github.com/mozgsml/fastapi_crud_generator.git"
```

## Quick start

```python
from fastapi import FastAPI
from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter

app = FastAPI()

adapter = SQLModelAdapter(get_session=get_session, model=Article)

crud = CRUDCollection(orm_adapter=adapter)

app.include_router(crud.get_router(), prefix="/articles", tags=["articles"])
```
