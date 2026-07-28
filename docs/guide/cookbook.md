# Cookbook

Task-oriented recipes. Every one is exercised by a test in the suite —
the "Tested by" line points at it, so the code here is known to run (and
runs against every configured ORM backend).

Examples assume you already have an adapter:

```python
adapter = SQLModelAdapter(model=Category, get_session=get_session)
```

## Disable endpoints

Drop the routes you don't want to expose.

```python
crud = CRUDCollection(
    orm_adapter=adapter,
    disable_delete=True,
    disable_create=True,
)
```

The path stays registered for its remaining methods, so a call to a
disabled one returns `405`, not `404`.

*Tested by `tests/integration/test_disable.py`.*

## Expose only some fields

Restrict which model fields feed the generated schemas instead of
writing a schema by hand.

```python
crud = CRUDCollection(
    orm_adapter=adapter,
    public_fields={"id", "title", "summary"},  # what GET returns
    create_fields={"title", "content"},         # what POST accepts
    update_fields={"title", "content", "summary"},
)
```

The same sets can live on the model as a `crud_config` class variable.

*Tested by `tests/test_sqlmodel_schema_generation.py`.*

## Use a custom primary-key path

Supply your own `pk_fields` model to route on a non-`id` column.

```python
class SlugPK(BaseModel):
    slug: str

crud = CRUDCollection(orm_adapter=adapter, pk_fields=SlugPK)
# -> GET /{slug}
```

*Tested by `tests/test_sqlmodel_crud_collection_pk.py`.*

## Nested collections

Mount one collection under another; the child is automatically scoped to
its parent by the foreign key, and the parent id is taken from the URL,
not the request body.

```python
thread_crud = CRUDCollection(orm_adapter=make_adapter(Thread))
post_crud = CRUDCollection(orm_adapter=make_adapter(Post))
thread_crud.add_nested_collection("/posts", post_crud)

app.include_router(thread_crud.get_router(prefix="/threads"))
# -> /threads/{thread_id}/posts, /threads/{thread_id}/posts/{post_id}
```

Nesting works several levels deep, in either FK direction, and with
composite keys.

*Tested by `tests/integration/test_nested.py`, `test_root_posts.py`,
`test_composite.py`.*

## A /me singleton collection

Serve `/users/me` — where the record is identified by the auth token,
not a path id. Combine two overrides: replace the PK dependency with one
that reads the current user, and pin the path segment to `/me`.

```python
class UserPK(BaseModel):
    id: int

async def get_me() -> UserPK:
    return UserPK(id=current_user_id())  # from your auth

class UserMeCRUD(CRUDCollection):
    dependency_overrides = {
        PKFieldsDependency: Annotated[UserPK, Depends(get_me)],
    }

    def get_id_path(self, exclude=frozenset()) -> str:
        return "/me"

user_me_crud = UserMeCRUD(orm_adapter=make_adapter(User))
user_me_crud.add_nested_collection("/posts", CRUDCollection(orm_adapter=make_adapter(Post)))
app.include_router(user_me_crud.get_router(prefix="/users"))
# -> /users/me, /users/me/posts  (no {user_id} anywhere)
```

*Tested by `tests/integration/test_user_posts.py`.*

## Add a custom route to a collection

Use `collection.extra` to hang your own routes off a generated
collection — no `get_router` override, no manual `add_api_route`. Bare
verbs anchor on the **single object** (mounted under `get_id_path`);
`.collection` anchors on the **collection root**. Both accept every
`APIRouter` keyword (`response_model=`, `dependencies=`, `status_code=`).

```python
user_me_crud = UserMeCRUD(orm_adapter=make_adapter(User))

@user_me_crud.extra.post("/avatar", response_model=UserPublic)
async def upload_avatar(
    file: Annotated[UploadFile, File()],
) -> User:
    ...
# -> POST /users/me/avatar   (item anchor: under get_id_path)

@user_me_crud.extra.collection.get("/search")
async def search_users(q: str) -> list[UserPublic]:
    ...
# -> GET /users/search       (collection anchor: at the root)
```

To receive the object's primary key, declare a parameter with the
`PKFieldsDependency` marker — it is injected exactly as for `get_one`,
**including every ancestor key when the collection is nested**, so a
handler never spells out parent ids:

```python
@post_crud.extra.get("/whoami")
async def whoami(pk: Annotated[BaseModel, PKFieldsDependency]) -> dict:
    return {"id": pk.id}
# nested -> GET /categories/{category_id}/threads/{thread_id}/posts/{post_id}/whoami
```

`extra.item` is an explicit alias for the bare form. Collection-root
extras are matched before `/{pk}`, so a literal segment like `/search`
is never swallowed by the get-one route.

*Tested by `tests/integration/test_extra_routes.py`.*

## Return a fallback instead of 404

Override `get_one_not_found` to return a value when the row is missing.
The same hook is how you create-on-first-access.

```python
class WithFallback(CRUDCollection):
    orm_adapter = adapter

    async def get_one_not_found(self, pk_values, include_data):
        return self.public_schema(id=0, name="fallback")
# GET a missing id -> 200 with the fallback body
```

*Tested by `tests/integration/test_override_hooks.py`.*

## Pre-process input in a handler

Override a route handler to run logic around the adapter call. **Keep the
marker annotations** — they are what turns the parameters into real
request inputs; drop them and the request 422s.

```python
class PrefixName(CRUDCollection):
    orm_adapter = adapter

    async def create_one_handler(
        self,
        create_data: Annotated[BaseModel, CreateSchemaDependency],
        parent_refs: Annotated[list, ParentPKFieldsDependency],
    ):
        create_data.name = f"PFX-{create_data.name}"
        return await super().create_one_handler(create_data, parent_refs)
```

*Tested by `tests/integration/test_override_hooks.py`.*

## Restrict which relations can be included

Pass an `include_schema` that only allows chosen relations; anything else
is rejected with `422`.

```python
class PostIncludeThreadOnly(BaseModel):
    include: list[Literal["thread"]] | None = None

crud = CRUDCollection(orm_adapter=adapter, include_schema=PostIncludeThreadOnly)
# ?include=thread -> 200 ; ?include=posts -> 422
```

*Tested by `tests/integration/test_include.py`.*

## Load several relations at once

Repeat the `include` query parameter — one entry per relation. A
comma-joined value is **not** supported and returns `422`.

```text
GET /threads/{id}?include=category&include=posts   # both loaded
GET /threads/{id}?include=category,posts           # 422
```

*Tested by `tests/integration/test_include_multi.py`.*
