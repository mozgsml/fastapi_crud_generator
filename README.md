# fastapi-crud-generator

Генератор CRUD-маршрутов для FastAPI. Позволяет быстро подключить стандартные эндпоинты (get one, get many, create, update, delete) к любому ORM через адаптер.

## Установка

```bash
# из GitHub
pip install git+https://github.com/mozgsml/fastapi_crud_generator.git

# с поддержкой SQLModel
pip install "fastapi-crud-generator[sqlmodel] @ git+https://github.com/mozgsml/fastapi_crud_generator.git"

# через uv
uv add git+https://github.com/mozgsml/fastapi_crud_generator
```

## Быстрый старт

```python
from fastapi import FastAPI
from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter  # если используется SQLModel

app = FastAPI()

crud = CRUDCollection(
    orm_adapter=SQLModelAdapter(MyModel, get_session),
    public_schema=MyPublicSchema,
    create_schema=MyCreateSchema,
    update_schema=MyUpdateSchema,
)

app.include_router(crud.get_router(), prefix="/items", tags=["items"])
```

## Параметры CRUDCollection

| Параметр | Описание |
|---|---|
| `orm_adapter` | Адаптер ORM (обязательный) |
| `public_schema` | Pydantic-схема для чтения |
| `public_list_schema` | Схема для списка (по умолчанию `PaginatorPage[public_schema]`) |
| `create_schema` | Схема для создания |
| `update_schema` | Схема для обновления |
| `pk_fields` | Pydantic-модель с полями первичного ключа (по умолчанию `Id_UUID`) |
| `filter_schema` | Схема фильтрации (генерируется автоматически из `public_schema`) |
| `sort_schema` | Схема сортировки (генерируется автоматически) |
| `include_schema` | Схема для включения связанных данных |

### Отключение отдельных маршрутов

```python
crud = CRUDCollection(
    orm_adapter=...,
    public_schema=...,
    disable_delete=True,
    disable_create=True,
)
```

### Зависимости FastAPI

```python
crud = CRUDCollection(
    orm_adapter=...,
    public_schema=...,
    dependencies=[Depends(require_auth)],        # для всех маршрутов
    get_many_dependencies=[Depends(require_admin)],  # только для GET /
    create_dependencies=[Depends(require_admin)],
)
```

## Свой ORM-адаптер

Унаследуй `ORMAdapterBase` и реализуй методы:

```python
from fastapi_crud_generator.orm.base import ORMAdapterBase

class MyAdapter(ORMAdapterBase):
    async def get_many_endpoint(self, ...): ...
    async def get_one_endpoint(self, ...): ...
    async def create_one_endpoint(self, ...): ...
    async def update_one_endpoint(self, ...): ...
    async def delete_one_endpoint(self, ...): ...
```
