"""Loading several relations at once.

The parameter repeats — ?include=category&include=posts — rather than
taking a comma-separated list; a comma-joined value is rejected as 422.
"""
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from fastapi_crud_generator import CRUDCollection


def _flat_app(make_adapter, forum_models):
    app = FastAPI()
    for model, prefix in (
        (forum_models.Category, "/categories"),
        (forum_models.Thread, "/threads"),
        (forum_models.Post, "/posts"),
    ):
        app.include_router(
            CRUDCollection(orm_adapter=make_adapter(model)).get_router(
                prefix=prefix,
            ),
        )
    return app


async def _seed_thread_with_post(client) -> int:
    cat = (await client.post("/categories", json={"name": "Py"})).json()
    thread = (
        await client.post(
            "/threads", json={"category_id": cat["id"], "title": "T"},
        )
    ).json()
    await client.post(
        "/posts", json={"thread_id": thread["id"], "slug": "p1"},
    )
    return thread["id"]


async def test_repeated_include_loads_every_relation(
    make_adapter, forum_models,
):
    app = _flat_app(make_adapter, forum_models)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
    ) as c:
        thread_id = await _seed_thread_with_post(c)
        r = await c.get(
            f"/threads/{thread_id}",
            params=[("include", "category"), ("include", "posts")],
        )

    assert r.status_code == 200
    body = r.json()
    assert body["category"] is not None
    assert len(body["posts"]) == 1


async def test_comma_separated_include_is_rejected(make_adapter, forum_models):
    app = _flat_app(make_adapter, forum_models)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
    ) as c:
        thread_id = await _seed_thread_with_post(c)
        r = await c.get(
            f"/threads/{thread_id}", params={"include": "category,posts"},
        )

    assert r.status_code == 422
