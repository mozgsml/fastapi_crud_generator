"""SQLAlchemy (pure DeclarativeBase) backend for integration tests."""
import os
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

import examples.forum.orm.sqlalchemy as forum_models
from fastapi_crud_generator.orm.sqlalchemy import SQLAlchemyAdapter
from tests.integration.backends import (
    MYSQL_URL_ENV,
    POSTGRES_URL_ENV,
    BackendContext,
)

_Base = forum_models.Base


def _make_factory(engine: AsyncEngine):
    session_factory = async_sessionmaker(
        engine, expire_on_commit=False,
    )

    def make_adapter(model):
        async def get_session():
            async with session_factory() as session:
                yield session

        return SQLAlchemyAdapter(model=model, get_session=get_session)

    return make_adapter


@asynccontextmanager
async def _backend(url: str, *, drop_after: bool = False):
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)
    try:
        yield BackendContext(
            make_adapter=_make_factory(engine),
            models=forum_models,
        )
    finally:
        if drop_after:
            async with engine.begin() as conn:
                await conn.run_sync(_Base.metadata.drop_all)
        await engine.dispose()


@asynccontextmanager
async def sqlalchemy_sqlite():
    async with _backend("sqlite+aiosqlite:///:memory:") as backend:
        yield backend


@asynccontextmanager
async def sqlalchemy_postgres():
    async with _backend(
        os.environ[POSTGRES_URL_ENV], drop_after=True,
    ) as backend:
        yield backend


@asynccontextmanager
async def sqlalchemy_mysql():
    async with _backend(
        os.environ[MYSQL_URL_ENV], drop_after=True,
    ) as backend:
        yield backend
