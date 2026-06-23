"""Integration test infrastructure — ORM/DB agnostic.

Active backends are discovered at import time via try/except.
A backend is skipped silently if its package is not installed
or its env var is not set.
"""
import os

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from fastapi_crud_generator import CRUDCollection
from tests.integration.backends import MYSQL_URL_ENV, POSTGRES_URL_ENV

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
