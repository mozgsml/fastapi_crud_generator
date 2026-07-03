# fastapi-crud-generator

[![Tests](https://github.com/mozgsml/fastapi_crud_generator/actions/workflows/tests.yml/badge.svg)](https://github.com/mozgsml/fastapi_crud_generator/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/fastapi-crud-generator)](https://pypi.org/project/fastapi-crud-generator/)
[![Python](https://img.shields.io/pypi/pyversions/fastapi-crud-generator)](https://pypi.org/project/fastapi-crud-generator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.txt)

Подключает полноценный CRUD к FastAPI без написания схем, фильтров и пагинации вручную.
Схемы генерируются из ORM-модели автоматически.

```python
from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter

crud = CRUDCollection(orm_adapter=SQLModelAdapter(model=Article, get_session=get_session))
app.include_router(crud.get_router(prefix="/articles", tags=["articles"]))
```

Три строки — и готовы пять эндпоинтов с фильтрацией, сортировкой и пагинацией:

```
GET    /articles              ?title=…&published=true&sort=created_at:desc&page=1&per_page=20
GET    /articles/{article_id}
POST   /articles
PATCH  /articles/{article_id}
DELETE /articles/{article_id}
```

## Установка

Если SQLModel, SQLAlchemy или Tortoise уже есть в проекте:

```bash
pip install fastapi-crud-generator
```

Если нужно установить ORM вместе с пакетом:

```bash
pip install "fastapi-crud-generator[sqlmodel]"
pip install "fastapi-crud-generator[sqlalchemy]"
pip install "fastapi-crud-generator[tortoise]"
```

## Документация

**[mozgsml.github.io/fastapi_crud_generator](https://mozgsml.github.io/fastapi_crud_generator)**

- [Getting Started](https://mozgsml.github.io/fastapi_crud_generator/guide/getting-started/) — полный пример с нуля
- [Schema Generation](https://mozgsml.github.io/fastapi_crud_generator/guide/schema-generation/) — как управлять полями схем
- [Nested Resources](https://mozgsml.github.io/fastapi_crud_generator/guide/nested-resources/) — `/threads/{id}/posts/{id}`
- [Custom Adapter](https://mozgsml.github.io/fastapi_crud_generator/custom-adapter/) — подключить свой ORM

## License

MIT
