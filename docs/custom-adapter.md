# Custom Adapter

Если нужно подключить ORM или источник данных, для которого нет готового адаптера,
реализуйте `ORMAdapterBase`.

## Интерфейс

```python
from fastapi_crud_generator.orm.base import ORMAdapterBase
from fastapi_crud_generator.schemas import PaginatorPage, ParentRef
from pydantic import BaseModel

class MyAdapter(ORMAdapterBase):
    # Генерация схем
    def generate_public_schema(self, fields=None, base_fields=None) -> type[BaseModel]: ...
    def generate_create_schema(self, fields=None, base_fields=None, exclude_related=None) -> type[BaseModel]: ...
    def generate_update_schema(self, fields=None, base_fields=None) -> type[BaseModel]: ...
    def generate_pk_schema(self) -> type[BaseModel]: ...
    def generate_include_schema(self) -> type[BaseModel]: ...

    # CRUD-операции
    async def get_one(self, pk_values, include_data, parent_refs=None): ...
    async def get_many(self, filter_data, sort_data, include_data, paginator, parent_refs=None): ...
    async def create_one(self, data, parent_refs=None): ...
    async def update_one(self, pk_values, data, parent_refs=None): ...
    async def delete_one(self, pk_values, parent_refs=None): ...
```

## Пример: простое хранилище в памяти

```python
from pydantic import BaseModel, create_model
from fastapi_crud_generator.orm.base import ORMAdapterBase
from fastapi_crud_generator.schemas import NotFoundError, PaginatorPage

_store: dict[int, dict] = {}
_next_id = 1

class ItemPublic(BaseModel):
    id: int
    name: str
    price: float

class ItemCreate(BaseModel):
    name: str
    price: float

class ItemUpdate(BaseModel):
    name: str | None = None
    price: float | None = None

class ItemPK(BaseModel):
    id: int

class InMemoryAdapter(ORMAdapterBase):
    model = None

    def generate_public_schema(self, fields=None, base_fields=None):
        return ItemPublic

    def generate_create_schema(self, fields=None, base_fields=None, exclude_related=None):
        return ItemCreate

    def generate_update_schema(self, fields=None, base_fields=None):
        return ItemUpdate

    def generate_pk_schema(self):
        return ItemPK

    def generate_include_schema(self):
        return create_model("ItemInclude")

    async def get_one(self, pk_values, include_data, parent_refs=None):
        return _store.get(pk_values.id)

    async def get_many(self, filter_data, sort_data, include_data, paginator, parent_refs=None):
        items = list(_store.values())
        total = len(items)
        page = items[paginator.offset : paginator.offset + paginator.limit]
        return {"page": paginator.page, "per_page": paginator.per_page, "count": total, "data": page}

    async def create_one(self, data, parent_refs=None):
        global _next_id
        item = {"id": _next_id, **data.model_dump()}
        _store[_next_id] = item
        _next_id += 1
        return item

    async def update_one(self, pk_values, data, parent_refs=None):
        if pk_values.id not in _store:
            raise NotFoundError
        for k, v in data.model_dump(exclude_none=True).items():
            _store[pk_values.id][k] = v

    async def delete_one(self, pk_values, parent_refs=None):
        return _store.pop(pk_values.id, None)
```

Подключение:

```python
crud = CRUDCollection(orm_adapter=InMemoryAdapter())
app.include_router(crud.get_router(prefix="/items"))
```

## `parent_refs`

В вложенных ресурсах методы получают `parent_refs` — список `ParentRef`
с информацией о родительских объектах:

```python
from fastapi_crud_generator.schemas import ParentRef

async def get_many(self, filter_data, sort_data, include_data, paginator, parent_refs=None):
    query = select(Post)
    for ref in (parent_refs or []):
        if ref.model is Thread:
            query = query.where(Post.thread_id == ref.pk_values.thread_id)
    ...
```

## Полная документация интерфейса

See [API Reference](api-reference.md#ORMAdapterBase).
