# Pagination

## Формат ответа

`GET /` всегда возвращает объект `PaginatorPage`:

```json
{
  "page": 1,
  "per_page": 20,
  "count": 142,
  "data": [...]
}
```

`count` — общее количество объектов (с учётом фильтров), а не количество в `data`.

## Query-параметры

```
GET /articles?page=3&per_page=10
```

| Параметр | По умолчанию | Ограничения |
|---|---|---|
| `page` | 1 | ≥ 1 |
| `per_page` | 20 | ≥ 0 |

`per_page=0` возвращает все записи без ограничений.

## Кастомный пагинатор

Если нужна другая логика пагинации — унаследуйтесь от `PaginatorBase`:

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

Передайте пагинатор через адаптер или напрямую в `CRUDCollection` через `dependency_overrides`.
