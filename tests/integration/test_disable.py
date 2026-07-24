"""disable_* flags remove the corresponding route."""
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from fastapi_crud_generator import CRUDCollection


def _build_app(make_adapter, model):
    class NoDelete(CRUDCollection):
        disable_delete = True

    app = FastAPI()
    app.include_router(
        NoDelete(orm_adapter=make_adapter(model)).get_router(
            prefix="/categories",
        ),
    )
    return app


def test_disabled_route_is_not_registered(make_adapter, forum_models):
    app = _build_app(make_adapter, forum_models.Category)

    methods_by_path: dict[str, set[str]] = {}
    for route in app.routes:
        path = getattr(route, "path", "")
        methods_by_path.setdefault(path, set()).update(
            getattr(route, "methods", set()) or set(),
        )

    single = "/categories/{category_id}"
    assert "DELETE" not in methods_by_path.get(single, set())
    # sibling operations on the same path are untouched
    assert "GET" in methods_by_path[single]
    assert "PATCH" in methods_by_path[single]


async def test_disabled_route_returns_405(make_adapter, forum_models):
    app = _build_app(make_adapter, forum_models.Category)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
    ) as c:
        created = (
            await c.post("/categories", json={"name": "keep me"})
        ).json()
        r = await c.delete(f"/categories/{created['id']}")

    assert r.status_code == 405  # path exists for GET/PATCH, DELETE removed
