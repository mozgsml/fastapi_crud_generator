# Filtering & Sorting

## Фильтрация

Фильтр-схема генерируется автоматически из public-схемы. Все скалярные поля
(`int`, `float`, `str`, `bool`, enum) становятся опциональными query-параметрами.

```
GET /articles?published=true
GET /articles?title=hello
GET /articles?published=false&title=draft
```

Поля-отношения (FK-объекты, списки) в фильтр не попадают — только примитивные типы.

### Кастомный фильтр

Если нужна другая логика (например, фильтр по диапазону дат) — передайте свою схему:

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
    При использовании кастомного фильтра адаптер передаёт его в `get_many` как есть.
    Логику применения фильтра нужно реализовать в адаптере — стандартный адаптер
    применяет только поля, совпадающие по имени с колонками модели.

## Сортировка

Сортировка тоже генерируется автоматически. Для каждого скалярного поля доступно
три варианта:

```
GET /articles?sort=title          # по умолчанию asc
GET /articles?sort=title:asc
GET /articles?sort=title:desc
```

Можно передать несколько значений:

```
GET /articles?sort=published:desc&sort=title:asc
```

### Кастомная сортировка

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
