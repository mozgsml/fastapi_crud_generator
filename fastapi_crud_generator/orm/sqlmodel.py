from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Query
from pydantic import BaseModel, create_model
from pydantic_core import PydanticUndefined

from fastapi_crud_generator.config import CRUDConfigDict
from fastapi_crud_generator.orm.base import ORMAdapterBase
from fastapi_crud_generator.paginator import PaginatorBase
from fastapi_crud_generator.schemas import PaginatorPage
from fastapi_crud_generator.utils import slice_model

try:
    from sqlalchemy import Select, desc, func
    from sqlmodel import SQLModel, select, update
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlmodel.main import FieldInfoMetadata
except ImportError:
    SQLMODEL_INSTALLED = False
else:
    SQLMODEL_INSTALLED = True


class SQLModelPaginator(PaginatorBase):
    async def paginate(
            self, session: AsyncSession,
            query: Select,
        ) -> PaginatorPage:
        # pylint: disable=not-callable
        return {
            'count': await session.scalar(
                select(func.count()).select_from(query.subquery())
            ),
            'page': self.page,
            'per_page': self.per_page,
            'data':  (await session.exec(
                query.limit(self.limit).offset(self.offset))).all(),
        }


class SQLModelAdapter(ORMAdapterBase):
    """ORM adapter for SQLModel with async SQLAlchemy sessions.

    Implements schema generation by introspecting SQLModel metadata:
    primary keys via ``__table__.primary_key``, server-generated fields
    via ``server_default``, and output-only fields via ``exclude=True``.
    ORM-specific ``FieldInfoMetadata`` is stripped from all generated schemas
    so the resulting Pydantic models are clean of SQLAlchemy internals.

    Args:
        get_session: Async generator that yields an ``AsyncSession``.
        model: The SQLModel table class to operate on.
    """

    get_session: Callable[[], AsyncGenerator[AsyncSession, None, None]] = None
    model: SQLModel | None = None
    paginator_class = SQLModelPaginator

    def __init__(self, *,
        get_session: Callable[
            [], AsyncGenerator[AsyncSession, None, None]
        ] = None,
        model: SQLModel | None = None,
    ):
        assert SQLMODEL_INSTALLED, "sqlmodel is not installed"
        self.get_session = get_session or self.__class__.get_session
        self.model = model or self.model
        assert self.get_session, "get_session is required"
        assert self.model, "model is required"

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None, None]:
        async for s in self.get_session():
            yield s

    def get_crud_config(self) -> CRUDConfigDict:
        return getattr(self.model, 'crud_config', CRUDConfigDict())

    def get_pk_field_names(self) -> set[str]:
        return {col.name for col in self.model.__table__.primary_key.columns}

    def get_server_generated_field_names(self) -> set[str]:
        """Return field names backed by a column with server_default."""
        result = set()
        for name, field_info in self.model.model_fields.items():
            for meta in field_info.metadata:
                if isinstance(meta, FieldInfoMetadata):
                    sa_column = meta.sa_column
                    if (sa_column is not PydanticUndefined
                            and sa_column is not None
                            and sa_column.server_default is not None):
                        result.add(name)
        return result

    def get_default_public_fields(self) -> set[str]:
        """Return all model field names that are not explicitly excluded."""
        return {
            name
            for name, field_info in self.model.model_fields.items()
            if field_info.exclude is not True
        }

    def get_default_create_fields(self) -> set[str]:
        """Return field names except PKs and server-generated fields."""
        auto_fields = (
            self.get_pk_field_names() | self.get_server_generated_field_names()
        )
        return {
            name
            for name in self.model.model_fields
            if name not in auto_fields
        }

    def generate_public_schema(
        self,
        fields: set[str] | None = None,
        base_fields: set[str] | None = None,
    ) -> type[BaseModel]:
        crud_config = self.get_crud_config()
        resolved_public = fields or (crud_config.public_fields or None)
        resolved_base = base_fields or (crud_config.base_fields or None)

        if resolved_public is None and resolved_base is None:
            effective_fields = (
                self.get_default_public_fields() | self.get_pk_field_names()
            )
        else:
            effective_fields = (
                (resolved_public or set()) | (resolved_base or set())
            )

        return slice_model(
            f"{self.model.__name__}Public",
            self.model,
            fields=effective_fields,
            exclude_metadata=(FieldInfoMetadata,),
        )

    def generate_create_schema(
        self,
        fields: set[str] | None = None,
        base_fields: set[str] | None = None,
    ) -> type[BaseModel]:
        crud_config = self.get_crud_config()
        resolved_create = fields or (crud_config.create_fields or None)
        resolved_base = base_fields or (crud_config.base_fields or None)

        if resolved_create is None and resolved_base is None:
            effective_fields = self.get_default_create_fields()
        else:
            effective_fields = (
                (resolved_create or set()) | (resolved_base or set())
            )

        return slice_model(
            f"{self.model.__name__}Create",
            self.model,
            fields=effective_fields,
            exclude_metadata=(FieldInfoMetadata,),
        )

    def generate_update_schema(
        self,
        fields: set[str] | None = None,
        base_fields: set[str] | None = None,
    ) -> type[BaseModel]:
        crud_config = self.get_crud_config()
        resolved_update = fields or (crud_config.update_fields or None)
        resolved_base = base_fields or (crud_config.base_fields or None)

        if resolved_update is None and resolved_base is None:
            effective_fields = self.get_default_create_fields()
        else:
            effective_fields = (
                (resolved_update or set()) | (resolved_base or set())
            )

        return slice_model(
            f"{self.model.__name__}Update",
            self.model,
            fields=effective_fields,
            optional=True,
            exclude_metadata=(FieldInfoMetadata,),
        )

    def generate_include_schema(self) -> BaseModel:
        """Build a query schema for selecting which relationships to include.

        Creates a Pydantic model with an ``include`` field typed as
        ``Literal[<relationship names>]``, so FastAPI validates that only
        existing relationship names are accepted as query parameters.
        """
        fields_names = tuple(
            self.model.__sqlmodel_relationships__.keys()
        )
        if not fields_names:
            return create_model(f"{self.model.__name__}Include")
        literal_type = Literal.__getitem__(fields_names)
        return create_model(
            f"{self.model.__name__}Include",
            include=(
                Annotated[list[literal_type] | None, Query()],
                None,
            ),
        )

    def get_base_list_queryset(self) -> Select:
        return select(self.model)

    def apply_queryset_filter(
        self,
        statement: Select,
        filter_model: BaseModel,
    ) -> Select:
        filter_dict = filter_model.model_dump(exclude_unset=True)
        for key, value in filter_dict.items():
            statement = statement.where(getattr(self.model, key) == value)
        return statement

    def apply_queryset_sort(
        self,
        statement: Select,
        sort_data: BaseModel,
    ) -> Select:
        assert len(sort_data.model_fields) == 1, (
            "Only one sort argument is supported")
        sort_dict = sort_data.model_dump(exclude_unset=True)

        if len(sort_dict) == 0:
            return statement

        sort_value = next(iter(sort_dict.values()))
        if not isinstance(sort_value, list):
            sort_value = [sort_value]

        added_sort_fields = []
        for value in sort_value:
            field, *direction = value.split(":", 2)
            if field not in added_sort_fields:
                added_sort_fields.append(field)
                attr = getattr(self.model, field)
                if len(direction) and direction[0] == 'desc':
                    attr = desc(attr)
                statement = statement.order_by(attr)

        return statement

    def include_related(
        self,
        statement: Select,
        include_data: BaseModel,
    ) -> Select:
        return statement

    def get_base_single_queryset(self) -> Select:
        return select(self.model)

    async def get_one(
        self, pk_values: BaseModel, include_data: BaseModel,
    ) -> SQLModel | None:
        """Return a single object by primary key, or None if not found."""
        statement = self.get_base_single_queryset()
        for key, value in pk_values.model_dump().items():
            statement = statement.where(getattr(self.model, key) == value)
        statement = self.include_related(statement, include_data)
        async with self.session() as session:
            return (await session.exec(statement)).first()

    async def get_many(
        self,
        filter_data: BaseModel,
        sort_data: BaseModel,
        include_data: BaseModel,
        paginator: SQLModelPaginator,
    ) -> PaginatorPage:
        """Return a paginated, filtered, sorted list."""
        statement = self.get_base_list_queryset()
        statement = self.apply_queryset_filter(statement, filter_data)
        statement = self.apply_queryset_sort(statement, sort_data)
        statement = self.include_related(statement, include_data)
        async with self.session() as session:
            return await paginator.paginate(session, statement)

    async def create_one(self, data: BaseModel) -> SQLModel:
        """Persist a new object and return it."""
        item = self.model.model_validate(data)
        async with self.session() as session:
            session.add(item)
            await session.commit()
            await session.refresh(item)
        return item

    async def update_one(
        self,
        pk_values: BaseModel,
        data: BaseModel,
    ) -> None:
        """Update an existing object by primary key."""
        new_values = data.model_dump(exclude_unset=True)
        statement = update(self.model)
        for key, value in pk_values.model_dump().items():
            statement = statement.where(getattr(self.model, key) == value)
        statement = statement.values(**new_values)
        async with self.session() as session:
            await session.exec(statement)
            await session.commit()

    async def delete_one(self, pk_values: BaseModel) -> SQLModel | None:
        """Delete an object by primary key and return it, or None."""
        statement = self.get_base_single_queryset()
        for key, value in pk_values.model_dump().items():
            statement = statement.where(getattr(self.model, key) == value)
        async with self.session() as session:
            result = (await session.exec(statement)).first()
            if result is None:
                return None
            await session.delete(result)
            await session.commit()
        return result
