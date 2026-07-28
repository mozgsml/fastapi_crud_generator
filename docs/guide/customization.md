# Customization

Every collection is configured in one of two interchangeable ways, and
its behaviour is tuned by overriding methods on a subclass. This page is
the reference for both. For task-oriented, copy-paste examples see the
[Cookbook](cookbook.md) — every recipe there is backed by a test.

## Two ways to configure

A setting can be passed to the constructor or declared as a class
attribute. They are equivalent; the constructor argument wins when both
are given.

```python
# constructor
crud = CRUDCollection(orm_adapter=adapter, disable_delete=True)

# class attribute — handy when several collections share config
class ArticleCRUD(CRUDCollection):
    orm_adapter = adapter
    disable_delete = True
```

Class attributes compose through normal inheritance:

```python
class AuthenticatedCRUD(CRUDCollection):
    dependencies = [Depends(require_auth)]

class ArticleCRUD(AuthenticatedCRUD):
    orm_adapter = SQLModelAdapter(model=Article, get_session=get_session)
```

## Options reference

### Adapter & primary key

| Option | Type | Default | Purpose |
| --- | --- | --- | --- |
| `orm_adapter` | `ORMAdapterBase` | — (required) | The ORM adapter all data access goes through. |
| `pk_fields` | `type[BaseModel]` | derived from adapter | Model of primary-key fields; drives the `/{...}` path params. |

### Schemas

Leave these unset to have them generated from the model; set one to take
full control of that shape.

| Option | Type | Default |
| --- | --- | --- |
| `public_schema` | `BaseModel` | `adapter.generate_public_schema(...)` |
| `public_list_schema` | `BaseModel` | `PaginatorPage[public_schema]` |
| `create_schema` | `BaseModel` | generated (lazily, see note) |
| `update_schema` | `BaseModel` | generated, all fields optional |
| `filter_schema` | `BaseModel` | one optional query field per scalar |
| `sort_schema` | `BaseModel` | `?sort=field:asc\|desc` values |
| `include_schema` | `BaseModel` | one entry per relation |
| `create_out_schema` / `update_out_schema` | any | `response_model` for POST / PATCH |

!!! note "`create_schema` is resolved lazily"
    Unlike the others, the create schema is finalised when the router is
    built, because a nested collection's strategy may drop the parent's
    foreign key from it. `self.create_schema` is therefore `None` on the
    instance — don't construct it directly inside a hook.

### Field selection

Instead of writing a whole schema, restrict which model fields feed the
generated ones:

| Option | Applies to |
| --- | --- |
| `base_fields` | fallback for all generated schemas |
| `public_fields` | the public (GET) schema |
| `create_fields` | the create (POST) schema |
| `update_fields` | the update (PATCH) schema |

The same sets can live on the model itself as a `crud_config` — see
[Schema Generation](schema-generation.md).

### Disabling endpoints

Each flag drops one route. `None` (the constructor default) means
"inherit the class attribute"; `True`/`False` set it outright.

| Option | Removes |
| --- | --- |
| `disable_get_many` | `GET /` |
| `disable_get_one` | `GET /{pk}` |
| `disable_create` | `POST /` |
| `disable_update` | `PATCH /{pk}` |
| `disable_delete` | `DELETE /{pk}` |

### Dependencies

| Option | Scope |
| --- | --- |
| `dependencies` | all routes of the collection |
| `get_one_dependencies` | `GET /{pk}` only |
| `get_many_dependencies` | `GET /` only |
| `create_dependencies` | `POST /` only |
| `update_dependencies` | `PATCH /{pk}` only |
| `delete_dependencies` | `DELETE /{pk}` only |

!!! warning "Pass collection-wide deps via `dependencies`, not `router_kwargs`"
    A `dependencies=` value smuggled through `**router_kwargs` is
    overwritten by `self.dependencies` when the router is built. Use the
    `dependencies` option.

### Other

| Option | Type | Purpose |
| --- | --- | --- |
| `dependency_overrides` | `dict[type, ...]` | Replace a dependency marker (see below). |
| `**router_kwargs` | — | Forwarded to `APIRouter(**...)` (tags, prefix, etc.). |

## Overridable methods

Subclass `CRUDCollection` and override what you need. Signatures below
are exact — match them.

### `get_id_path`

```python
def get_id_path(self, exclude: frozenset[str] = frozenset()) -> str
```

Returns the single-object path segment (default `/{article_id}`, built
from `pk_fields`). `exclude` drops params an ancestor already placed in
the path. Override it to pin a fixed segment for a token-scoped
singleton whose identity comes from auth rather than the URL:

```python
class UserMeCRUD(CRUDCollection):
    def get_id_path(self, exclude=frozenset()) -> str:
        return "/me"
```

See the [`/users/me` recipe](cookbook.md#a-me-singleton-collection).

### `get_one_not_found`

```python
async def get_one_not_found(self, pk_values, include_data) -> object
```

Called by `GET /{pk}` when the row is missing; the default raises
`HTTPException(404)`. This is the only formal not-found hook — for
create/update/delete the 404 is raised inside the handler itself.
Override it to return a fallback, or to create-on-first-access.

### Route handlers

```python
async def get_one_handler(self, pk_field_values, include_data, parent_refs)
async def get_many_handler(self, paginator, filter_data, sort_data, include_data, parent_refs)
async def create_one_handler(self, create_data, parent_refs)
async def update_one_handler(self, pk_field_values, update_data, parent_refs)
async def delete_one_handler(self, pk_field_values, parent_refs)
```

Override a handler to pre- or post-process around the adapter call.

!!! danger "Keep the marker annotations"
    Each handler parameter is annotated `Annotated[..., XDependency]`.
    Those markers are what the router rewrites into real request params.
    An override with plain, unannotated parameters makes them leak into
    the query string and the request fails with 422. Copy the annotations
    verbatim — see the [handler recipe](cookbook.md#pre-process-input-in-a-handler).

### `apply_pk_aliases` and `generate_unique_id`

```python
def apply_pk_aliases(self, pk_schema: type[BaseModel]) -> type[BaseModel]
def generate_unique_id(self, route: APIRoute) -> str
```

`apply_pk_aliases` adds the `{model}_id` alias to bare PK fields (so `id`
becomes `{article_id}` in the path); override to change that naming.
`generate_unique_id` builds the OpenAPI operationId.

## Adding your own routes with `extra`

When you need an endpoint the generator does not produce (`/avatar`,
`/publish`, `/search`), register it on `collection.extra` instead of
overriding `get_router`. `extra` is a small registrar exposing the
FastAPI verb decorators; the routes are merged into `get_router()` with
the same dependency wiring as the generated routes.

```python
collection.extra.get(path, **api_route_kwargs)      # item anchor
collection.extra.post(path, ...)                    # (also put/patch/
collection.extra.delete(path, ...)                  #  delete/api_route)
collection.extra.item                               # alias for the above
collection.extra.collection.get(path, ...)          # collection anchor
```

| Anchor | How to register | Where it mounts |
| --- | --- | --- |
| **Single object** | `extra.<verb>` (or `extra.item.<verb>`) | under `get_id_path` — `/{pk}/...`, or `/me/...` for a pinned segment |
| **Collection root** | `extra.collection.<verb>` | at the collection root — `/...` |

Both anchors reuse the strategy overrides of the CRUD routes, so a
handler can declare `Annotated[BaseModel, PKFieldsDependency]` (and
`Annotated[list, ParentPKFieldsDependency]`) to receive the object's key
— **and every ancestor key when the collection is nested** — without
naming any path param. Collection-root extras are registered before
`/{pk}`, so a literal segment such as `/search` is not captured by the
get-one route.

Any `APIRouter` keyword (`response_model=`, `dependencies=`,
`status_code=`, `tags=`) passes straight through. See the
[custom-route recipe](cookbook.md#add-a-custom-route-to-a-collection).

## Replacing a dependency with `dependency_overrides`

Handlers declare their inputs as marker classes from
`fastapi_crud_generator.deps` (e.g. `PKFieldsDependency`,
`CreateSchemaDependency`). `dependency_overrides` swaps the
implementation behind a marker — the key is the marker class, the value
is either a `ReplaceSignatureDependency` or a raw annotation (which is
wrapped automatically).

The canonical use is replacing the primary key with a value from auth,
so `/{pk}` becomes token-scoped:

```python
class UserMeCRUD(CRUDCollection):
    dependency_overrides = {
        PKFieldsDependency: Annotated[UserPK, Depends(get_current_user)],
    }
```

Markers you can override: `CreateSchemaDependency`,
`UpdateSchemaDependency`, `PublicSchemaDependency`,
`PublicListSchemaDependency`, `FilterSchemaDependency`,
`SortSchemaDependency`, `IncludeSchemaDependency`, `PKFieldsDependency`,
`PaginatorDependency`, `ParentPKFieldsDependency`.
