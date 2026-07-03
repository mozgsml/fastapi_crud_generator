# Nested Resources

Вложенные ресурсы позволяют строить иерархические маршруты вида
`/threads/{thread_id}/posts/{post_id}`.

## Базовый пример

```python
from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter

thread_crud = CRUDCollection(orm_adapter=SQLModelAdapter(model=Thread, get_session=get_session))
post_crud   = CRUDCollection(orm_adapter=SQLModelAdapter(model=Post,   get_session=get_session))

thread_crud.add_nested_collection("/posts", post_crud)

app.include_router(thread_crud.get_router(prefix="/threads"))
```

Результирующие маршруты:

```
GET    /threads
GET    /threads/{thread_id}
POST   /threads
PATCH  /threads/{thread_id}
DELETE /threads/{thread_id}

GET    /threads/{thread_id}/posts
GET    /threads/{thread_id}/posts/{post_id}
POST   /threads/{thread_id}/posts
PATCH  /threads/{thread_id}/posts/{post_id}
DELETE /threads/{thread_id}/posts/{post_id}
```

## Трёхуровневая вложенность

```python
category_crud = CRUDCollection(orm_adapter=SQLModelAdapter(model=Category, get_session=get_session))
thread_crud   = CRUDCollection(orm_adapter=SQLModelAdapter(model=Thread,   get_session=get_session))
post_crud     = CRUDCollection(orm_adapter=SQLModelAdapter(model=Post,     get_session=get_session))

thread_crud.add_nested_collection("/posts", post_crud)
category_crud.add_nested_collection("/threads", thread_crud)

app.include_router(category_crud.get_router(prefix="/categories"))
# → /categories/{category_id}/threads/{thread_id}/posts/{post_id}
```

## Как работает фильтрация по родителю

Когда приходит запрос `GET /threads/{thread_id}/posts`, адаптер получает `parent_refs` —
список объектов `ParentRef` с моделью и PK родителя:

```python
@dataclass
class ParentRef:
    model: type  # Thread
    pk_values: BaseModel  # { thread_id: 42 }
```

Стандартные адаптеры (SQLModel, SQLAlchemy, Tortoise) автоматически применяют
`WHERE post.thread_id = 42` к выборке и при создании устанавливают `thread_id = 42`.

## Настройка тегов для вложенных роутеров

```python
from fastapi_crud_generator.config import NestedConfig

thread_crud.add_nested_collection(
    "/posts",
    post_crud,
    config=NestedConfig(router_kwargs={"tags": ["posts"]}),
)
```
