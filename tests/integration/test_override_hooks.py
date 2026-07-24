"""Overriding the not-found hook and a route handler in a subclass."""
from typing import Annotated

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.deps import (
    CreateSchemaDependency,
    ParentPKFieldsDependency,
)


async def test_get_one_not_found_override_replaces_the_404(
    make_adapter, forum_models,
):
    """get_one_not_found may return a value instead of raising 404."""
    adapter = make_adapter(forum_models.Category)

    class WithFallback(CRUDCollection):
        orm_adapter = adapter

        async def get_one_not_found(self, pk_values, include_data):
            return self.public_schema(
                id=0, name="fallback", created_at=None, updated_at=None,
            )

    app = FastAPI()
    app.include_router(WithFallback().get_router(prefix="/categories"))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
    ) as c:
        r = await c.get("/categories/999")

    assert r.status_code == 200
    assert r.json()["name"] == "fallback"


async def test_create_handler_override_mutates_input(
    make_adapter, forum_models,
):
    """A handler override must keep the marker annotations in its signature.

    Those Annotated[..., XDependency] markers are what the router rewrites
    into real request params; drop them and the params leak into the query
    string (422). With them kept, the override can pre-process the data and
    delegate to super().
    """
    adapter = make_adapter(forum_models.Category)

    class PrefixName(CRUDCollection):
        orm_adapter = adapter

        async def create_one_handler(
            self,
            create_data: Annotated[BaseModel, CreateSchemaDependency],
            parent_refs: Annotated[list, ParentPKFieldsDependency],
        ):
            create_data.name = f"PFX-{create_data.name}"
            return await super().create_one_handler(create_data, parent_refs)

    app = FastAPI()
    app.include_router(PrefixName().get_router(prefix="/categories"))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
    ) as c:
        r = await c.post("/categories", json={"name": "hello"})

    assert r.status_code == 200
    assert r.json()["name"] == "PFX-hello"
