# Pagination

## Response format

Every `GET /` response is a `PaginatorPage` object:

```json
{
  "page": 1,
  "per_page": 20,
  "count": 142,
  "data": [...]
}
```

`count` is the total number of matching objects, not the number of items in `data`.

## Query parameters

```
GET /articles?page=3&per_page=10
```

| Parameter | Default | Constraint |
|---|---|---|
| `page` | 1 | ≥ 1 |
| `per_page` | 20 | ≥ 0 |

`per_page=0` returns all records without limit.

## Custom paginator

Subclass `PaginatorBase` to implement different pagination logic:

```python
from fastapi import Query
from fastapi_crud_generator.paginator import PaginatorBase
from fastapi_crud_generator.schemas import PaginatorPage

class CursorPaginator(PaginatorBase):
    def __init__(self, cursor: int = Query(0, ge=0), limit: int = Query(20, ge=1)):
        self.cursor = cursor
        self.limit = limit

    async def paginate(self, session, query) -> PaginatorPage:
        data = (await session.exec(query.where(Model.id > self.cursor).limit(self.limit))).all()
        return {"page": 1, "per_page": self.limit, "count": len(data), "data": data}
```

Pass the custom paginator class through the adapter or via `dependency_overrides` in `CRUDCollection`.
