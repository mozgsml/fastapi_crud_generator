# Filtering & Sorting

## Filtering

A filter schema is generated automatically from the public schema. All scalar fields
(`int`, `float`, `str`, `bool`, enum) become optional query parameters.

```
GET /articles?published=true
GET /articles?title=hello
GET /articles?published=false&title=draft
```

Relation fields (FK objects, lists) are excluded — only primitive types are supported.

### Custom filter schema

If you need different logic (e.g. date range filtering), pass your own schema:

```python
from pydantic import BaseModel
from datetime import date

class ArticleFilter(BaseModel):
    published: bool | None = None
    created_after: date | None = None
    created_before: date | None = None

crud = CRUDCollection(
    orm_adapter=adapter,
    filter_schema=ArticleFilter,
)
```

!!! note
    With a custom filter schema, the adapter receives it as-is in `get_many`.
    The standard adapters apply only fields that match model column names by exact match.
    For range filters or custom logic, override the adapter's `get_many` method.

## Sorting

Sorting is also generated automatically. For each scalar field, three variants are available:

```
GET /articles?sort=title          # ascending by default
GET /articles?sort=title:asc
GET /articles?sort=title:desc
```

Multiple sort fields are supported:

```
GET /articles?sort=published:desc&sort=title:asc
```

### Custom sort schema

```python
from typing import Literal
from pydantic import BaseModel

class ArticleSort(BaseModel):
    sort: list[Literal["title", "title:asc", "title:desc", "created_at:desc"]] | None = None

crud = CRUDCollection(
    orm_adapter=adapter,
    sort_schema=ArticleSort,
)
```
