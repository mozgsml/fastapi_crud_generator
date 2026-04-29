from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from tkinter import NO
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, create_model

from fastapi_crud_generator.deps import (
    CreateSchemaDependency,
    FilterSchemaDependency,
    IncludeSchemaDependency,
    PKFieldsDependency,
    SortSchemaDependency,
    UpdateSchemaDependency,
)
from fastapi_crud_generator.orm.base import ORMAdapterBase
from fastapi_crud_generator.paginator import PaginatorBase
from fastapi_crud_generator.schemas import PaginatorPage

try:
    from sqlalchemy import Select, desc, func
    from sqlmodel import SQLModel, select, update
    from sqlmodel.ext.asyncio.session import AsyncSession
except ImportError:
    SQLMODEL_INSTALLED = False
else:
    SQLMODEL_INSTALLED = True


class SQLModelPaginator(PaginatorBase):
    async def paginate(
            self, session:AsyncSession,
            query: Select,
        ) -> PaginatorPage:
        # pylint: disable=not-callable
        return {
            'count': await session.scalar(select(func.count()).select_from(query.subquery())),
            'page': self.page,
            'per_page': self.per_page,
            'data':  (await session.exec(
                query.limit(self.limit).offset(self.offset))).all(),
        }


class SQLModelAdapter(ORMAdapterBase):
    get_session: Callable[[], AsyncGenerator[AsyncSession, None, None]] = None
    model: SQLModel | None = None

    def __init__(self, *,
        get_session: Callable[[], AsyncGenerator[AsyncSession, None, None]] = None,
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

    def generate_include_schema(self) -> BaseModel:
        fields_names = self.model.__sqlmodel_relationships__.keys()
        literal_type = Literal.__getitem__(tuple(fields_names))
        result = create_model(
            f"{self.model.__name__}Include",
            include=(Annotated[list[literal_type] | None, Query()], None),
        )
        return result

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
        assert len(sort_data.model_fields) == 1 , (
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

    async def get_many_endpoint(self,
        paginator: Annotated[SQLModelPaginator, Depends(SQLModelPaginator)],
        filter_data: Annotated[BaseModel, FilterSchemaDependency],
        sort_data: Annotated[BaseModel, SortSchemaDependency],
        include_data: Annotated[BaseModel, IncludeSchemaDependency],
    ):
        statement = self.get_base_list_queryset()
        statement = self.apply_queryset_filter(statement, filter_data)
        statement = self.apply_queryset_sort(statement, sort_data)
        statement = self.include_related(statement, include_data)
        async with self.session() as session:
            result = await paginator.paginate(
                session,
                statement,
            )
        return result

    def get_base_single_queryset(self):
        return select(self.model)

    async def get_one_endpoint(
            self,
            pk_field_values: Annotated[BaseModel, PKFieldsDependency],
    ):
        statement = self.get_base_single_queryset()
        for key, value in pk_field_values.model_dump().items():
            statement = statement.where(getattr(self.model, key) == value)
        async with self.session() as session:
            result = (await session.exec(statement)).first()

        if not result:
            raise HTTPException(status_code=404, detail="Not found")

        return result

    async def create_one_endpoint(
        self,
        create_data: Annotated[BaseModel, CreateSchemaDependency],
    ):
        item = self.model.model_validate(create_data)
        async with self.session() as session:
            session.add(item)
            await session.commit()
            await session.refresh(item)
        return item

    async def create_many_endpoint(self):
        pass

    async def update_one_endpoint(
            self,
            pk_field_values: Annotated[BaseModel, PKFieldsDependency],
            update_data: Annotated[BaseModel, UpdateSchemaDependency],
        ):
        new_values = update_data.model_dump(exclude_unset=True)
        statement = update(self.model)
        for key, value in pk_field_values.model_dump().items():
            statement = statement.where(getattr(self.model, key) == value)

        statement = statement.values(**new_values)

        async with self.session() as session:
            await session.exec(statement)
            await session.commit()


    async def update_many_endpoint(self):
        pass

    async def delete_one_endpoint(
            self,
            pk_field_values: Annotated[BaseModel, PKFieldsDependency],
        ):
        statement = select(self.model)
        for key, value in pk_field_values.model_dump().items():
            statement = statement.where(getattr(self.model, key) == value)
        async with self.session() as session:
            result = (await session.exec(statement)).first()

            if not result:
                raise HTTPException(status_code=404, detail="Not found")

            await session.delete(result)
            await session.commit()

        return result
