from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Literal

from pydantic import BaseModel, create_model
from pydantic_core import PydanticUndefined

from fastapi_crud_generator.config import CRUDConfigDict
from fastapi_crud_generator.orm.base import ORMAdapterBase
from fastapi_crud_generator.paginator import PaginatorBase
from fastapi_crud_generator.schemas import (
    NotFoundError,
    PaginatorPage,
    ParentNotFoundError,
    ParentRef,
)
from fastapi_crud_generator.utils import slice_model

try:
    from sqlalchemy import Select, desc, func
    from sqlalchemy.orm import joinedload, noload, selectinload
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
    model: type[SQLModel] | None = None
    paginator_class = SQLModelPaginator

    def __init__(self, *,
        get_session: Callable[  # noqa: RUF013
            [], AsyncGenerator[AsyncSession, None, None],
        ] = None,
        model: type[SQLModel] | None = None,
    ):
        if not SQLMODEL_INSTALLED:
            raise ImportError("sqlmodel is not installed")
        self.get_session = get_session or self.__class__.get_session
        self.model = model or self.model
        if not self.get_session:
            raise ValueError("get_session is required")
        if not self.model:
            raise ValueError("model is required")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None, None]:
        async for s in self.get_session():
            yield s

    def get_model_name(self) -> str:  # noqa: D102
        return self.model.__name__.lower()

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

    def get_default_create_fields(
        self, exclude_related: list[type] | None = None,
    ) -> set[str]:
        """Return field names except auto-generated PKs and server fields.

        A PK field is excluded when it has no default (auto-increment/uuid4)
        or when it is a FK pointing to a model in ``exclude_related`` —
        meaning its value comes from the parent URL, not the request body.
        """
        pk_names = self.get_pk_field_names()
        related_tables = {m.__table__ for m in (exclude_related or [])}
        fk_from_related = {
            fk.parent.name
            for fk in self.model.__table__.foreign_keys
            if fk.column.table in related_tables
        }
        auto_pks = {
            name
            for name, field_info in self.model.model_fields.items()
            if name in pk_names and not field_info.is_required()
        }
        auto_fields = auto_pks | fk_from_related | self.get_server_generated_field_names()
        return {
            name
            for name in self.model.model_fields
            if name not in auto_fields
        }

    def generate_flat_public_schema(
        self,
        fields: set[str] | None = None,
        base_fields: set[str] | None = None,
    ) -> type[BaseModel]:
        """Build a schema from model fields only, without relationships."""
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

    def generate_public_schema(
        self,
        fields: set[str] | None = None,
        base_fields: set[str] | None = None,
    ) -> type[BaseModel]:
        base = self.generate_flat_public_schema(fields, base_fields)

        rel_fields: dict[str, Any] = {}
        for rel_name, rel_prop in self.model.__mapper__.relationships.items():
            related_cls = rel_prop.mapper.class_
            tmp = object.__new__(SQLModelAdapter)
            tmp.model = related_cls
            related_schema = tmp.generate_flat_public_schema()
            field_type = (
                list[related_schema] if rel_prop.uselist else related_schema
            )
            rel_fields[rel_name] = (field_type | None, None)

        if not rel_fields:
            return base

        return create_model(base.__name__, __base__=base, **rel_fields)

    def generate_create_schema(
        self,
        fields: set[str] | None = None,
        base_fields: set[str] | None = None,
        exclude_related: list[type] | None = None,
    ) -> type[BaseModel]:
        crud_config = self.get_crud_config()
        resolved_create = fields or (crud_config.create_fields or None)
        resolved_base = base_fields or (crud_config.base_fields or None)

        if resolved_create is None and resolved_base is None:
            effective_fields = self.get_default_create_fields(exclude_related)
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

    def get_default_update_fields(self) -> set[str]:
        """Return field names except all PKs and server-generated fields.

        Unlike create, ALL PK fields are excluded — they come from the URL
        path and must never be changed via the request body.
        """
        excluded = self.get_pk_field_names() | self.get_server_generated_field_names()
        return {name for name in self.model.model_fields if name not in excluded}

    def generate_update_schema(
        self,
        fields: set[str] | None = None,
        base_fields: set[str] | None = None,
    ) -> type[BaseModel]:
        crud_config = self.get_crud_config()
        resolved_update = fields or (crud_config.update_fields or None)
        resolved_base = base_fields or (crud_config.base_fields or None)

        if resolved_update is None and resolved_base is None:
            effective_fields = self.get_default_update_fields()
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

    def generate_pk_schema(self) -> type[BaseModel]:
        """Build a Pydantic model containing only the primary key fields."""
        return slice_model(
            f"{self.model.__name__}PK",
            self.model,
            fields=self.get_pk_field_names(),
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
            include=(list[literal_type] | None, None),
        )

    def _apply_parent_refs(
        self, stmt: Select, parent_refs: list[ParentRef],
    ) -> Select:
        """JOIN to each parent and WHERE on its PK fields.

        Join condition is inferred from declared FKs. Override for
        non-FK joins or non-standard PK field names.
        """
        for parent_ref in parent_refs:
            stmt = stmt.join(parent_ref.model)
            for field, value in parent_ref.pk_values.model_dump().items():
                stmt = stmt.where(
                    getattr(parent_ref.model, field) == value,
                )
        return stmt

    def get_base_list_queryset(
        self, parent_refs: list[ParentRef] | None = None,
    ) -> Select:
        """Build the base SELECT for list ops, scoped to parent."""
        stmt = select(self.model)
        if not parent_refs:
            return stmt
        return self._apply_parent_refs(stmt, parent_refs)

    def get_base_single_queryset(
        self, parent_refs: list[ParentRef] | None = None,
    ) -> Select:
        """Build the base SELECT for single-record ops, scoped to parent."""
        stmt = select(self.model)
        if not parent_refs:
            return stmt
        return self._apply_parent_refs(stmt, parent_refs)

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
        if len(type(sort_data).model_fields) != 1:
            raise ValueError("Only one sort argument is supported")
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
        requested = set(getattr(include_data, "include", None) or [])
        for rel_name, rel_prop in (
            self.model.__mapper__.relationships.items()
        ):
            rel_attr = getattr(self.model, rel_name)
            if rel_name in requested:
                opt = (
                    selectinload(rel_attr)
                    if rel_prop.uselist
                    else joinedload(rel_attr)
                )
            else:
                opt = noload(rel_attr)
            statement = statement.options(opt)
        return statement

    def _nullify_unloaded_relations(
        self, instance: SQLModel, include_data: BaseModel,
    ) -> None:
        """Set non-requested relationship attributes to None on the instance.

        noload() leaves collections as [] instead of None, making it
        impossible to distinguish "not requested" from "empty loaded".
        Direct __dict__ write bypasses the collection adapter; safe here
        because no further ORM operations occur on the instance after this.
        """
        requested = set(getattr(include_data, "include", None) or [])
        for rel_name in self.model.__mapper__.relationships.keys():
            if rel_name not in requested:
                instance.__dict__[rel_name] = None

    async def get_one(
        self,
        pk_values: BaseModel,
        include_data: BaseModel,
        parent_refs: list[ParentRef] | None = None,
    ) -> SQLModel | None:
        """Return a single object by primary key, or None if not found."""
        statement = self.get_base_single_queryset(parent_refs=parent_refs)
        for key, value in pk_values.model_dump().items():
            statement = statement.where(getattr(self.model, key) == value)
        statement = self.include_related(statement, include_data)
        async with self.session() as session:
            result = (await session.exec(statement)).first()
            if result is not None:
                self._nullify_unloaded_relations(result, include_data)
            return result

    async def get_many(
        self,
        filter_data: BaseModel,
        sort_data: BaseModel,
        include_data: BaseModel,
        paginator: SQLModelPaginator,
        parent_refs: list[ParentRef] | None = None,
    ) -> PaginatorPage:
        """Return a paginated, filtered, sorted list."""
        statement = self.get_base_list_queryset(parent_refs=parent_refs)
        statement = self.apply_queryset_filter(statement, filter_data)
        statement = self.apply_queryset_sort(statement, sort_data)
        statement = self.include_related(statement, include_data)
        async with self.session() as session:
            page = await paginator.paginate(session, statement)
            for item in page["data"]:
                self._nullify_unloaded_relations(item, include_data)
            return page

    def _fk_values_from_parent(self, parent_ref: ParentRef) -> dict:
        """Map parent PK values to child FK column names via declared FKs."""
        parent_table = parent_ref.model.__table__
        result = {}
        for fk in self.model.__table__.foreign_keys:
            if fk.column.table is parent_table:
                value = getattr(parent_ref.pk_values, fk.column.name, None)
                if value is not None:
                    result[fk.parent.name] = value
        return result

    def _verify_parent_chain_stmt(
        self, parent_refs: list[ParentRef],
    ) -> Select:
        """SELECT to check direct parent exists within the ancestor chain."""
        direct = parent_refs[0]
        stmt = select(direct.model)
        stmt = self._apply_parent_refs(stmt, parent_refs[1:])
        for field, value in direct.pk_values.model_dump().items():
            stmt = stmt.where(getattr(direct.model, field) == value)
        return stmt

    async def create_one(
        self,
        data: BaseModel,
        parent_refs: list[ParentRef] | None = None,
    ) -> SQLModel:
        """Persist a new object, verifying the parent chain first."""
        data_dict = data.model_dump()
        async with self.session() as session:
            if parent_refs:
                stmt = self._verify_parent_chain_stmt(parent_refs)
                if (await session.exec(stmt)).first() is None:
                    raise ParentNotFoundError
                for ref in parent_refs:
                    data_dict.update(self._fk_values_from_parent(ref))
            item = self.model.model_validate(data_dict)
            session.add(item)
            await session.commit()
            await session.refresh(item)
        return item

    async def update_one(
        self,
        pk_values: BaseModel,
        data: BaseModel,
        parent_refs: list[ParentRef] | None = None,
    ) -> None:
        """Update an existing object by primary key, scoped to parent chain."""
        in_scope = True
        async with self.session() as session:
            if parent_refs:
                check = self.get_base_single_queryset(parent_refs=parent_refs)
                for key, value in pk_values.model_dump().items():
                    check = check.where(getattr(self.model, key) == value)
                in_scope = (await session.exec(check)).first() is not None
            if in_scope:
                new_values = data.model_dump(exclude_unset=True)
                statement = update(self.model)
                for key, value in pk_values.model_dump().items():
                    statement = statement.where(getattr(self.model, key) == value)
                statement = statement.values(**new_values)
                await session.exec(statement)
                await session.commit()
        if not in_scope:
            raise NotFoundError

    async def delete_one(
        self,
        pk_values: BaseModel,
        parent_refs: list[ParentRef] | None = None,
    ) -> SQLModel | None:
        """Delete an object by primary key, scoped to parent chain."""
        statement = self.get_base_single_queryset(parent_refs=parent_refs)
        for key, value in pk_values.model_dump().items():
            statement = statement.where(getattr(self.model, key) == value)
        async with self.session() as session:
            result = (await session.exec(statement)).first()
            if result is None:
                return None
            await session.delete(result)
            await session.commit()
        return result
