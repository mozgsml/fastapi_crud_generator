"""Tests for ?include= eager loading via include_related."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from typing import Literal

from fastapi_crud_generator import CRUDCollection


@pytest.fixture
def include_app(make_adapter, forum_models):
    app = FastAPI()
    app.include_router(
        CRUDCollection(
            orm_adapter=make_adapter(forum_models.Category),
        ).get_router(prefix="/categories"),
    )
    app.include_router(
        CRUDCollection(
            orm_adapter=make_adapter(forum_models.Thread),
        ).get_router(prefix="/threads"),
    )
    app.include_router(
        CRUDCollection(
            orm_adapter=make_adapter(forum_models.Post),
        ).get_router(prefix="/posts"),
    )
    return app


@pytest.fixture
async def include_client(include_app):
    async with AsyncClient(
        transport=ASGITransport(app=include_app), base_url="http://test",
    ) as c:
        yield c


async def _setup(c) -> tuple[dict, dict, dict]:
    cat = (await c.post("/categories", json={"name": "Python"})).json()
    thread = (await c.post(
        "/threads", json={"title": "Async", "category_id": cat["id"]},
    )).json()
    post = (await c.post(
        "/posts", json={"slug": "asyncio", "thread_id": thread["id"]},
    )).json()
    return cat, thread, post


async def test_include_posts_in_thread(include_client) -> None:
    """GET /threads/{id}?include=posts returns thread with nested posts."""
    _cat, thread, post = await _setup(include_client)

    r = await include_client.get(f"/threads/{thread['id']}?include=posts")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == thread["id"]
    assert len(data["posts"]) == 1
    assert data["posts"][0]["id"] == post["id"]
    assert data["posts"][0]["slug"] == post["slug"]


async def test_without_include_posts_is_null(include_client) -> None:
    """Without ?include=posts, posts field is null (not loaded)."""
    _cat, thread, _post = await _setup(include_client)

    r = await include_client.get(f"/threads/{thread['id']}")
    assert r.status_code == 200
    assert r.json()["posts"] is None


async def test_include_posts_empty(include_client) -> None:
    """Thread with no posts returns empty list when included."""
    cat = (await include_client.post(
        "/categories", json={"name": "Empty"},
    )).json()
    thread = (await include_client.post(
        "/threads", json={"title": "No posts", "category_id": cat["id"]},
    )).json()

    r = await include_client.get(f"/threads/{thread['id']}?include=posts")
    assert r.status_code == 200
    assert r.json()["posts"] == []


async def test_include_thread_in_post(include_client) -> None:
    """GET /posts/{id}?include=thread returns post with nested thread."""
    _cat, thread, post = await _setup(include_client)

    r = await include_client.get(f"/posts/{post['id']}?include=thread")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == post["id"]
    assert data["thread"]["id"] == thread["id"]
    assert data["thread"]["title"] == thread["title"]


async def test_include_thread_null_without_param(include_client) -> None:
    """Without ?include=thread, thread field is null in post response."""
    _cat, _thread, post = await _setup(include_client)

    r = await include_client.get(f"/posts/{post['id']}")
    assert r.status_code == 200
    assert r.json()["thread"] is None


# --- custom include_schema ---


class _PostIncludeThreadOnly(BaseModel):
    include: list[Literal["thread"]] | None = None


@pytest.fixture
def custom_include_app(make_adapter, forum_models):
    """App where Post allows only ?include=thread, not other relations."""
    app = FastAPI()
    app.include_router(
        CRUDCollection(
            orm_adapter=make_adapter(forum_models.Category),
        ).get_router(prefix="/categories"),
    )
    app.include_router(
        CRUDCollection(
            orm_adapter=make_adapter(forum_models.Thread),
        ).get_router(prefix="/threads"),
    )
    app.include_router(
        CRUDCollection(
            orm_adapter=make_adapter(forum_models.Post),
            include_schema=_PostIncludeThreadOnly,
        ).get_router(prefix="/posts"),
    )
    return app


@pytest.fixture
async def custom_include_client(custom_include_app):
    async with AsyncClient(
        transport=ASGITransport(app=custom_include_app), base_url="http://test",
    ) as c:
        yield c


async def test_custom_include_schema_allowed(custom_include_client) -> None:
    """?include=thread works when thread is in the custom include_schema.

    Nested thread uses a flat schema — no posts field inside it.
    """
    _cat, thread, post = await _setup(custom_include_client)

    r = await custom_include_client.get(f"/posts/{post['id']}?include=thread")
    assert r.status_code == 200
    data = r.json()
    assert data["thread"]["id"] == thread["id"]
    assert data["thread"]["title"] == thread["title"]
    assert "posts" not in data["thread"]


async def test_custom_include_schema_rejected(custom_include_client) -> None:
    """?include=posts is rejected with 422 when not in the custom schema."""
    _cat, _thread, post = await _setup(custom_include_client)

    r = await custom_include_client.get(f"/posts/{post['id']}?include=posts")
    assert r.status_code == 422


# --- Thread has 2 relations: posts + category ---


class _ThreadIncludeCategoryOnly(BaseModel):
    include: list[Literal["category"]] | None = None


class _ThreadIncludePostsOnly(BaseModel):
    include: list[Literal["posts"]] | None = None


@pytest.fixture
def two_relations_app(make_adapter, forum_models):
    """Thread has posts and category.

    /threads      — include_schema allows only category
    /threads-alt  — include_schema allows only posts
    """
    app = FastAPI()
    app.include_router(
        CRUDCollection(
            orm_adapter=make_adapter(forum_models.Category),
        ).get_router(prefix="/categories"),
    )
    app.include_router(
        CRUDCollection(
            orm_adapter=make_adapter(forum_models.Thread),
            include_schema=_ThreadIncludeCategoryOnly,
        ).get_router(prefix="/threads"),
    )
    app.include_router(
        CRUDCollection(
            orm_adapter=make_adapter(forum_models.Thread),
            include_schema=_ThreadIncludePostsOnly,
        ).get_router(prefix="/threads-alt"),
    )
    return app


@pytest.fixture
async def two_relations_client(two_relations_app):
    async with AsyncClient(
        transport=ASGITransport(app=two_relations_app), base_url="http://test",
    ) as c:
        yield c


async def test_partial_include_schema_loads_allowed(two_relations_client) -> None:
    """?include=category loads category; posts is null on the thread object."""
    cat = (await two_relations_client.post(
        "/categories", json={"name": "Python"},
    )).json()
    thread = (await two_relations_client.post(
        "/threads", json={"title": "Async", "category_id": cat["id"]},
    )).json()

    r = await two_relations_client.get(
        f"/threads/{thread['id']}?include=category",
    )
    assert r.status_code == 200
    data = r.json()
    assert data["category"]["id"] == cat["id"]
    assert data["category"]["name"] == cat["name"]
    assert data["posts"] is None


async def test_partial_include_schema_posts_only(two_relations_client) -> None:
    """?include=posts on /threads-alt loads posts; category is null."""
    cat = (await two_relations_client.post(
        "/categories", json={"name": "Go"},
    )).json()
    thread = (await two_relations_client.post(
        "/threads-alt", json={"title": "Channels", "category_id": cat["id"]},
    )).json()

    r = await two_relations_client.get(
        f"/threads-alt/{thread['id']}?include=posts",
    )
    assert r.status_code == 200
    data = r.json()
    assert data["posts"] == []
    assert data["category"] is None
