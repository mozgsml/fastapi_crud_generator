# fastapi-crud-generator

[![Tests](https://github.com/mozgsml/fastapi_crud_generator/actions/workflows/tests.yml/badge.svg)](https://github.com/mozgsml/fastapi_crud_generator/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/fastapi-crud-generator)](https://pypi.org/project/fastapi-crud-generator/)
[![Python](https://img.shields.io/pypi/pyversions/fastapi-crud-generator)](https://pypi.org/project/fastapi-crud-generator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.txt)

Adds full CRUD routes to FastAPI without writing schemas, filters, or pagination by hand.
Everything is generated automatically from your ORM model.

```python
from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter

crud = CRUDCollection(orm_adapter=SQLModelAdapter(model=Article, get_session=get_session))
app.include_router(crud.get_router(prefix="/articles", tags=["articles"]))
```

Three lines — and five endpoints are ready with filtering, sorting, and pagination:

```
GET    /articles              ?title=…&published=true&sort=created_at:desc&page=1&per_page=20
GET    /articles/{article_id}
POST   /articles
PATCH  /articles/{article_id}
DELETE /articles/{article_id}
```

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

- [Getting Started](https://mozgsml.github.io/fastapi_crud_generator/guide/getting-started/) — full working example from scratch
- [Schema Generation](https://mozgsml.github.io/fastapi_crud_generator/guide/schema-generation/) — control which fields appear in each schema
- [Nested Resources](https://mozgsml.github.io/fastapi_crud_generator/guide/nested-resources/) — `/threads/{id}/posts/{id}`
- [Custom Adapter](https://mozgsml.github.io/fastapi_crud_generator/custom-adapter/) — connect your own ORM

## License

MIT
