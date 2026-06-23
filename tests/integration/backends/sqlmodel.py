"""SQLModel backends for integration tests.

Imported only when sqlmodel is installed (guarded by try/except in conftest).

Available backends:
  sqlmodel_sqlite   — in-memory SQLite, always available
  sqlmodel_postgres — requires env var POSTGRES_URL
  sqlmodel_mysql    — requires env var MYSQL_URL
"""
import os
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import examples.forum.orm.sqlmodel as forum_models
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter
from tests.integration.backends import (
    BackendContext,
    MYSQL_URL_ENV,
    POSTGRES_URL_ENV,
)


def _make_factory(engine: AsyncEngine):
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False,
    )

    def make_adapter(model):
        async def get_session():
            async with session_factory() as session:
                yield session

        return SQLModelAdapter(model=model, get_session=get_session)

    return make_adapter


@asynccontextmanager
async def _backend(url: str, *, drop_after: bool = False):
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    try:
        yield BackendContext(
            make_adapter=_make_factory(engine),
            models=forum_models,
        )
    finally:
        if drop_after:
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.drop_all)
        await engine.dispose()


@asynccontextmanager
async def sqlmodel_sqlite():
    async with _backend("sqlite+aiosqlite:///:memory:") as backend:
        yield backend


@asynccontextmanager
async def sqlmodel_postgres():
    async with _backend(
        os.environ[POSTGRES_URL_ENV], drop_after=True,
    ) as backend:
        yield backend


@asynccontextmanager
async def sqlmodel_mysql():
    async with _backend(
        os.environ[MYSQL_URL_ENV], drop_after=True,
    ) as backend:
        yield backend
