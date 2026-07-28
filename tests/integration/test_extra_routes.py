"""User-defined ``extra`` routes: item + collection anchors, nesting.

Every snippet shown in the guide's ``extra`` section is exercised here,
so the docs cannot drift from working code.

- item anchor (``extra.post``): mounted under ``get_id_path`` and handed
  the object's pk exactly like the generated ``get_one`` route;
- collection anchor (``extra.collection.get``): mounted at the collection
  root, and matched before ``/{pk}`` so a literal segment is not eaten;
- nesting: an item extra on a nested collection gets the full ancestor
  prefix and every pk injected — the handler never spells out keys.
"""
from typing import Annotated

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.deps import PKFieldsDependency


@pytest.fixture
def extra_app(make_adapter, forum_models):
    """Category (top level) + Post nested two deep, each with extras."""
    app = FastAPI()

    category_crud = CRUDCollection(
        orm_adapter=make_adapter(forum_models.Category),
    )
    thread_crud = CRUDCollection(
        orm_adapter=make_adapter(forum_models.Thread),
    )
    post_crud = CRUDCollection(orm_adapter=make_adapter(forum_models.Post))

    @category_crud.extra.get("/whoami")
    async def category_whoami(
        pk: Annotated[BaseModel, PKFieldsDependency],
    ) -> dict:
        return {"id": pk.id}

    @category_crud.extra.collection.get("/ping")
    async def category_ping() -> dict:
        return {"pong": True}

    @post_crud.extra.get("/whoami")
    async def post_whoami(
        pk: Annotated[BaseModel, PKFieldsDependency],
    ) -> dict:
        return {"id": pk.id}

    thread_crud.add_nested_collection("/posts", post_crud)
    category_crud.add_nested_collection("/threads", thread_crud)
    app.include_router(category_crud.get_router(prefix="/categories"))
    return app


@pytest.fixture
async def extra_client(extra_app):
    async with AsyncClient(
        transport=ASGITransport(app=extra_app), base_url="http://test",
    ) as c:
        yield c


def test_extra_routes_mounted_at_expected_paths(extra_app) -> None:
    """Anchors resolve to the right path shapes, including when nested."""
    paths = {getattr(r, "path", "") for r in extra_app.routes}

    # item anchor, top level -> under the object's id_path
    assert "/categories/{category_id}/whoami" in paths
    # collection anchor, top level -> at the collection root
    assert "/categories/ping" in paths
    # item anchor, nested -> full ancestor prefix, no manual keys
    assert (
        "/categories/{category_id}/threads/{thread_id}"
        "/posts/{post_id}/whoami" in paths
    )


async def test_item_extra_receives_object_pk(extra_client) -> None:
    """A bare ``extra.get`` handler is handed the single object's pk."""
    cat = (
        await extra_client.post("/categories", json={"name": "Py"})
    ).json()

    r = await extra_client.get(f"/categories/{cat['id']}/whoami")

    assert r.status_code == 200
    assert r.json() == {"id": cat["id"]}


async def test_collection_extra_served_at_root(extra_client) -> None:
    """``extra.collection`` mounts at the root and beats /{pk} matching."""
    r = await extra_client.get("/categories/ping")

    assert r.status_code == 200
    assert r.json() == {"pong": True}


async def test_nested_item_extra_injects_every_key(extra_client) -> None:
    """Nested item extra resolves ancestors + own pk with zero boilerplate."""
    cat = (
        await extra_client.post("/categories", json={"name": "Py"})
    ).json()
    thread = (
        await extra_client.post(
            f"/categories/{cat['id']}/threads", json={"title": "T"},
        )
    ).json()
    post = (
        await extra_client.post(
            f"/categories/{cat['id']}/threads/{thread['id']}/posts",
            json={"slug": "s"},
        )
    ).json()

    r = await extra_client.get(
        f"/categories/{cat['id']}/threads/{thread['id']}"
        f"/posts/{post['id']}/whoami",
    )

    assert r.status_code == 200
    assert r.json() == {"id": post["id"]}


def test_item_alias_targets_the_same_registrar(
    make_adapter, forum_models,
) -> None:
    """``extra`` and ``extra.item`` are one registrar; ``.collection`` is not."""
    crud = CRUDCollection(orm_adapter=make_adapter(forum_models.Category))

    @crud.extra.post("/a")
    async def _a() -> dict:
        return {}

    @crud.extra.item.post("/b")
    async def _b() -> dict:
        return {}

    assert crud.extra.item is crud.extra
    assert [path for _, path, *_ in crud.extra.specs] == ["/a", "/b"]
    assert crud.extra.collection.specs == []
