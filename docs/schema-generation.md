# Schema Generation

Adapters automatically build Pydantic schemas from the ORM model, so
in the simplest case you only need to provide the adapter:

```python
from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter

adapter = SQLModelAdapter(get_session=get_session, model=Article)

crud = CRUDCollection(orm_adapter=adapter)
```

Three schemas are generated automatically:

- **public** — all fields except those marked `exclude=True`, plus the
  primary key.
- **create** — all fields except primary keys and database-generated
  fields (e.g. `server_default`).
- **update** — same field set as create, but every field is optional
  (PATCH semantics).

For full resolution details see the [API Reference](api-reference.md).

---

## Customising field sets

### Option 1 — crud_config on the model

Place a `crud_config` class variable on the model to define field sets
once for all usages:

```python
from typing import ClassVar
from fastapi_crud_generator.config import CRUDConfigDict

class Article(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    content: str
    summary: str | None = None

    crud_config: ClassVar[CRUDConfigDict] = CRUDConfigDict(
        public_fields={'title', 'summary'},
        create_fields={'title', 'content'},
        update_fields={'title', 'content', 'summary'},
    )
```

> `crud_config` must be annotated as `ClassVar` — otherwise the ORM
> treats it as a model field.

The adapter picks it up automatically — no extra arguments needed.

### Option 2 — explicit fields at call time

Pass `fields` to override `crud_config` and adapter defaults for a
specific schema. The result contains exactly those fields:

```python
public = adapter.generate_public_schema(fields={'title', 'content'})
# result: title, content — no primary key added automatically
```

`base_fields` are merged on top of the main set without replacing it,
useful when several schemas share a common subset:

```python
public = adapter.generate_public_schema(
    fields={'title'},
    base_fields={'created_at'},
)
# result: title, created_at
```

---

## Using hand-written schemas

Generated schemas cover common cases, but you can always pass a
manually written Pydantic model instead:

```python
class ArticleUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    published: bool | None = None  # field not on the ORM model

crud = CRUDCollection(
    orm_adapter=adapter,
    update_schema=ArticleUpdate,
)
```

Mix and match — pass only the schemas you want to override, and let
the rest be generated automatically.
