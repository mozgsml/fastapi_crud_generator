"""Tortoise ORM backend for integration tests.

Limitations vs SQLModel/SQLAlchemy backends:
- Composite PKs are not supported by Tortoise; PostTranslation tests are
  skipped for this backend (the model uses unique_together instead).
- Tortoise uses different URL schemes (postgres://, mysql://) than
  SQLAlchemy (postgresql+asyncpg://, mysql+aiomysql://). The helpers
  below convert the shared POSTGRES_URL / MYSQL_URL env vars on the fly.
"""
import os
from contextlib import asynccontextmanager
from types import SimpleNamespace

from tortoise import Tortoise

import examples.forum.orm.tortoise as forum_models
from fastapi_crud_generator.orm.tortoise import TortoiseAdapter
from tests.integration.backends import (
    MYSQL_URL_ENV,
    POSTGRES_URL_ENV,
    BackendContext,
)

TORTOISE_SQLITE_URL = "sqlite://:memory:"

_MODULES = {"models": ["examples.forum.orm.tortoise"]}

_URL_PREFIXES = [
    ("postgresql+asyncpg://", "postgres://"),
    ("mysql+aiomysql://", "mysql://"),
    ("mysql+asyncmy://", "mysql://"),
]


def _to_tortoise_url(url: str) -> str:
    for sa_prefix, tortoise_prefix in _URL_PREFIXES:
        if url.startswith(sa_prefix):
            return tortoise_prefix + url[len(sa_prefix):]
    return url


def _make_factory():
    def make_adapter(model):
        return TortoiseAdapter(model=model)
    return make_adapter


@asynccontextmanager
async def _backend(db_url: str):
    await Tortoise.init(db_url=db_url, modules=_MODULES)
    await Tortoise.generate_schemas()
    try:
        yield BackendContext(
            make_adapter=_make_factory(),
            models=forum_models,
        )
    finally:
        await Tortoise.close_connections()


@asynccontextmanager
async def tortoise_sqlite():
    async with _backend(TORTOISE_SQLITE_URL) as backend:
        yield backend


@asynccontextmanager
async def tortoise_postgres():
    url = _to_tortoise_url(os.environ[POSTGRES_URL_ENV])
    async with _backend(url) as backend:
        yield backend


@asynccontextmanager
async def tortoise_mysql():
    url = _to_tortoise_url(os.environ[MYSQL_URL_ENV])
    async with _backend(url) as backend:
        yield backend
