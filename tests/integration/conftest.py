"""Integration test infrastructure — ORM/DB agnostic.

Active backends are discovered at import time via try/except.
A backend is skipped silently if its package is not installed
or its env var is not set.
"""
import os
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.deps import PKFieldsDependency
from tests.integration.backends import MYSQL_URL_ENV, POSTGRES_URL_ENV


class _StubUserPK(BaseModel):
    id: int


async def _get_me_pk() -> _StubUserPK:
    return _StubUserPK(id=1)

BACKENDS = []

try:
    from tests.integration.backends.sqlmodel import (
        sqlmodel_mysql,
        sqlmodel_postgres,
        sqlmodel_sqlite,
    )

    BACKENDS.append(sqlmodel_sqlite)
    if os.getenv(POSTGRES_URL_ENV):
        BACKENDS.append(sqlmodel_postgres)
    if os.getenv(MYSQL_URL_ENV):
        BACKENDS.append(sqlmodel_mysql)
except ImportError:
    pass

try:
    from tests.integration.backends.sqlalchemy import (
        sqlalchemy_mysql,
        sqlalchemy_postgres,
        sqlalchemy_sqlite,
    )

    BACKENDS.append(sqlalchemy_sqlite)
    if os.getenv(POSTGRES_URL_ENV):
        BACKENDS.append(sqlalchemy_postgres)
    if os.getenv(MYSQL_URL_ENV):
        BACKENDS.append(sqlalchemy_mysql)
except ImportError:
    pass

try:
    from tests.integration.backends.tortoise import (
        tortoise_mysql,
        tortoise_postgres,
        tortoise_sqlite,
    )

    BACKENDS.append(tortoise_sqlite)
    if os.getenv(POSTGRES_URL_ENV):
        BACKENDS.append(tortoise_postgres)
    if os.getenv(MYSQL_URL_ENV):
        BACKENDS.append(tortoise_mysql)
except ImportError:
    pass

# In CI each job sets PYTEST_ORM and PYTEST_DB to isolate one combination.
_orm_filter = os.getenv("PYTEST_ORM")
if _orm_filter:
    BACKENDS = [b for b in BACKENDS if b.__name__.startswith(_orm_filter)]

_db_filter = os.getenv("PYTEST_DB")
if _db_filter:
    BACKENDS = [b for b in BACKENDS if _db_filter in b.__name__]


def pytest_collection_modifyitems(items: list) -> None:
    """Skip tests that require composite PK support for Tortoise backends."""
    for item in items:
        if not hasattr(item, "callspec"):
            continue
        param_id: str = item.callspec.id
        if "tortoise" in param_id and "test_composite" in item.nodeid:
            item.add_marker(
                pytest.mark.skip(
                    reason="Tortoise ORM does not support composite PKs",
                )
            )


@pytest.fixture(params=BACKENDS, ids=lambda b: b.__name__)
async def _backend(request):
    async with request.param() as backend:
        yield backend


@pytest.fixture
def make_adapter(_backend):
    return _backend.make_adapter


@pytest.fixture
def forum_models(_backend):
    return _backend.models


@pytest.fixture
def forum_app(make_adapter, forum_models):
    """FastAPI app with all forum routes wired up."""
    app = FastAPI()

    # Category → Thread → Post  (3 levels)
    post_crud = CRUDCollection(orm_adapter=make_adapter(forum_models.Post))
    thread_crud = CRUDCollection(orm_adapter=make_adapter(forum_models.Thread))
    category_crud = CRUDCollection(
        orm_adapter=make_adapter(forum_models.Category),
    )
    thread_crud.add_nested_collection("/posts", post_crud)
    category_crud.add_nested_collection("/threads", thread_crud)
    app.include_router(category_crud.get_router(prefix="/categories"))

    # Post → PostTranslation  (composite PK)
    translation_crud = CRUDCollection(
        orm_adapter=make_adapter(forum_models.PostTranslation),
    )
    post_translation_crud = CRUDCollection(
        orm_adapter=make_adapter(forum_models.Post),
    )
    post_translation_crud.add_nested_collection(
        "/translations", translation_crud,
    )
    app.include_router(
        post_translation_crud.get_router(prefix="/posts"),
    )

    return app


@pytest.fixture
async def client(forum_app):
    async with AsyncClient(
        transport=ASGITransport(app=forum_app), base_url="http://test",
    ) as c:
        yield c


@pytest.fixture
def user_posts_app(make_adapter, forum_models):
    """App demonstrating /users/me pattern (stub PK dep) + nested posts."""
    app = FastAPI()

    # Category → Thread — needed so tests can satisfy Post.thread_id FK
    thread_crud = CRUDCollection(orm_adapter=make_adapter(forum_models.Thread))
    category_crud = CRUDCollection(
        orm_adapter=make_adapter(forum_models.Category),
    )
    category_crud.add_nested_collection("/threads", thread_crud)
    app.include_router(category_crud.get_router(prefix="/categories"))

    class _UserMeCRUD(CRUDCollection):
        """User CRUD where single-item routes use the stub as PK."""

        dependency_overrides = {  # noqa: RUF012
            PKFieldsDependency: Annotated[_StubUserPK, Depends(_get_me_pk)],
        }

        def get_id_path(
            self, exclude: frozenset[str] = frozenset(),  # noqa: ARG002
        ) -> str:
            return "/me"

    user_me_crud = _UserMeCRUD(orm_adapter=make_adapter(forum_models.User))
    me_posts_crud = CRUDCollection(orm_adapter=make_adapter(forum_models.Post))
    user_me_crud.add_nested_collection("/posts", me_posts_crud)
    app.include_router(user_me_crud.get_router(prefix="/users"))

    return app


@pytest.fixture
async def user_client(user_posts_app):
    async with AsyncClient(
        transport=ASGITransport(app=user_posts_app), base_url="http://test",
    ) as c:
        yield c


@pytest.fixture
def root_posts_app(make_adapter, forum_models):
    """Post at root — Thread and Category added as ancestors via add_nested_collection."""
    app = FastAPI()

    post_crud = CRUDCollection(orm_adapter=make_adapter(forum_models.Post))
    thread_crud = CRUDCollection(orm_adapter=make_adapter(forum_models.Thread))
    category_crud = CRUDCollection(
        orm_adapter=make_adapter(forum_models.Category),
    )

    # Bidirectional: FK metadata determines direction automatically
    post_crud.add_nested_collection("/threads", thread_crud)
    thread_crud.add_nested_collection("/categories", category_crud)

    # All three registered at flat roots; parent chains inferred from FKs
    app.include_router(category_crud.get_router(prefix="/categories"))
    app.include_router(thread_crud.get_router(prefix="/threads"))
    app.include_router(post_crud.get_router(prefix="/posts"))

    return app


@pytest.fixture
async def root_client(root_posts_app):
    async with AsyncClient(
        transport=ASGITransport(app=root_posts_app), base_url="http://test",
    ) as c:
        yield c
