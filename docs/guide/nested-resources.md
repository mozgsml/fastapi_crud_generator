# Nested Resources

Nested resources let you build hierarchical routes like `/threads/{thread_id}/posts/{post_id}`.

## Basic example

```python
from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter

thread_crud = CRUDCollection(orm_adapter=SQLModelAdapter(model=Thread, get_session=get_session))
post_crud   = CRUDCollection(orm_adapter=SQLModelAdapter(model=Post,   get_session=get_session))

thread_crud.add_nested_collection("/posts", post_crud)

app.include_router(thread_crud.get_router(prefix="/threads"))
```

Resulting routes:

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

## Three levels deep

```python
category_crud = CRUDCollection(orm_adapter=SQLModelAdapter(model=Category, get_session=get_session))
thread_crud   = CRUDCollection(orm_adapter=SQLModelAdapter(model=Thread,   get_session=get_session))
post_crud     = CRUDCollection(orm_adapter=SQLModelAdapter(model=Post,     get_session=get_session))

thread_crud.add_nested_collection("/posts", post_crud)
category_crud.add_nested_collection("/threads", thread_crud)

app.include_router(category_crud.get_router(prefix="/categories"))
# → /categories/{category_id}/threads/{thread_id}/posts/{post_id}
```

## How parent filtering works

When a request comes in for `GET /threads/{thread_id}/posts`, the adapter receives
`parent_refs` — a list of `ParentRef` objects containing the parent model and its PK:

```python
@dataclass
class ParentRef:
    model: type       # Thread
    pk_values: BaseModel  # { thread_id: 42 }
```

The built-in adapters (SQLModel, SQLAlchemy, Tortoise) automatically apply
`WHERE post.thread_id = 42` to queries and set `thread_id = 42` on creation.

## Router tags for nested collections

```python
from fastapi_crud_generator.config import NestedConfig

thread_crud.add_nested_collection(
    "/posts",
    post_crud,
    config=NestedConfig(router_kwargs={"tags": ["posts"]}),
)
```
