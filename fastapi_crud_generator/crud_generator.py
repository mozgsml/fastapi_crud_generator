import inspect
import re
import uuid
from abc import ABC
from collections.abc import Callable
from functools import wraps
from typing import Any, get_type_hints

from fastapi import APIRouter, Depends
from fastapi.routing import APIRoute
from pydantic import BaseModel

from fastapi_crud_generator.deps import (
    CreateSchemaDependency,
    FilterSchemaDependency,
    IncludeSchemaDependency,
    PKFieldsDependency,
    PublicListSchemaDependency,
    PublicSchemaDependency,
    ReplaceSignatureDependency,
    SortSchemaDependency,
    UpdateSchemaDependency,
)
from fastapi_crud_generator.config import CRUDConfigDict
from fastapi_crud_generator.orm.base import ORMAdapterBase
from fastapi_crud_generator.schemas import PaginatorPage
from fastapi_crud_generator.utils import create_filter_model, create_sort_schema


def _init_list_param(
    param: list | None,
    class_default: list | None,
) -> list:
    """Return param if provided, else fall back to class_default or []."""
    return param if param is not None else (class_default or [])


class Id_UUID(BaseModel):
    id: uuid.UUID

class CRUDCollectionBase(ABC):

    orm_adapter: ORMAdapterBase | None = None

    public_schema: BaseModel = None
    public_list_schema: BaseModel = None

    update_schema: BaseModel = None
    update_out_schema = Any

    create_schema: BaseModel = None
    create_out_schema = Any

    # TODO add pk schema generation
    pk_fields: BaseModel = Id_UUID

    base_fields: set[str] | None = None
    public_fields: set[str] | None = None
    create_fields: set[str] | None = None
    update_fields: set[str] | None = None

    filter_schema: BaseModel = None
    sort_schema: BaseModel = None
    # include related data
    include_schema: BaseModel = None

    dependency_overrides: dict[
        type[ReplaceSignatureDependency],
        ReplaceSignatureDependency,
    ] | None = None

    dependencies: list[Depends] | None = None
    get_one_dependencies: list[Depends] | None = None
    get_many_dependencies: list[Depends] | None = None
    create_dependencies: list[Depends] | None = None
    update_dependencies: list[Depends] | None = None
    delete_dependencies: list[Depends] | None = None

    disable_get_one: bool = False
    disable_get_many: bool = False
    disable_create: bool = False
    disable_update: bool = False
    disable_delete: bool = False

    router_kwargs: dict | None = None


    def __init__(
        self,
        orm_adapter: ORMAdapterBase = None,
        public_schema: BaseModel | None = None,
        public_list_schema: BaseModel | None = None,
        update_schema: BaseModel | None = None,
        update_out_schema: BaseModel | None = None,
        create_schema: BaseModel | None = None,
        create_out_schema: BaseModel | None = None,
        base_fields: set[str] | None = None,
        public_fields: set[str] | None = None,
        create_fields: set[str] | None = None,
        update_fields: set[str] | None = None,

        filter_schema: BaseModel | None = None,
        sort_schema: BaseModel | None = None,
        include_schema: BaseModel | None = None,

        pk_fields: BaseModel = None,

        dependencies: list[Depends] | None = None,
        get_one_dependencies: list[Depends] | None = None,
        get_many_dependencies: list[Depends] | None = None,
        create_dependencies: list[Depends] | None = None,
        update_dependencies: list[Depends] | None = None,
        delete_dependencies: list[Depends] | None = None,

        disable_get_one: bool | None = None,
        disable_get_many: bool | None = None,
        disable_create: bool | None = None,
        disable_update: bool | None = None,
        disable_delete: bool | None = None,

        dependency_overrides: dict[
            type[ReplaceSignatureDependency],
            ReplaceSignatureDependency,
        ] | None = None,

        **router_kwargs: dict,

    ):
        self.orm_adapter = orm_adapter if orm_adapter else self.orm_adapter
        self.verify_orm_adapter()

        self.base_fields = base_fields or self.base_fields
        self.public_fields = public_fields or self.public_fields
        self.create_fields = create_fields or self.create_fields
        self.update_fields = update_fields or self.update_fields

        self.public_schema = (
            public_schema
            or self.public_schema
            or self.orm_adapter.generate_public_schema(
                self.public_fields, self.base_fields,
            )
        )
        self.create_schema = (
            create_schema
            or self.create_schema
            or self.orm_adapter.generate_create_schema(
                self.create_fields, self.base_fields,
            )
        )
        self.update_schema = (
            update_schema
            or self.update_schema
            or self.orm_adapter.generate_update_schema(
                self.update_fields, self.base_fields,
            )
        )
        self.update_out_schema = update_out_schema or self.update_out_schema
        self.create_out_schema = create_out_schema or self.create_out_schema
        self.public_list_schema = (
            public_list_schema or
            self.public_list_schema or
            PaginatorPage[self.public_schema]
        )
        self.pk_fields = pk_fields or self.pk_fields
        self.filter_schema = filter_schema or self.filter_schema
        if self.filter_schema is None:
            self.filter_schema = create_filter_model(self.public_schema)
        self.sort_schema = sort_schema or self.sort_schema
        if self.sort_schema is None:
            self.sort_schema = create_sort_schema(self.public_schema)
        self.include_schema = include_schema or self.include_schema
        if self.include_schema is None:
            self.include_schema = self.orm_adapter.generate_include_schema()

        self.dependencies = _init_list_param(
            dependencies, self.dependencies)
        self.get_one_dependencies = _init_list_param(
            get_one_dependencies, self.get_one_dependencies)
        self.get_many_dependencies = _init_list_param(
            get_many_dependencies, self.get_many_dependencies)
        self.create_dependencies = _init_list_param(
            create_dependencies, self.create_dependencies)
        self.update_dependencies = _init_list_param(
            update_dependencies, self.update_dependencies)
        self.delete_dependencies = _init_list_param(
            delete_dependencies, self.delete_dependencies)

        self.disable_get_one = (disable_get_one if disable_get_one is not None
                                else self.disable_get_one)
        self.disable_get_many = (disable_get_many
                                 if disable_get_many is not None
                                 else self.disable_get_many)
        self.disable_create = (disable_create if disable_create is not None
                               else self.disable_create)
        self.disable_update = (disable_update if disable_update is not None
                               else self.disable_update)
        self.disable_delete = (disable_delete if disable_delete is not None
                               else self.disable_delete)

        self.dependency_overrides = (
            dependency_overrides if dependency_overrides is not None
            else (self.dependency_overrides or {})
        )
        self.router_kwargs = (
            router_kwargs if router_kwargs
            else dict(self.router_kwargs or {})
        )
        self.router_kwargs["dependencies"] = self.dependencies


    def verify_orm_adapter(self):
        assert self.orm_adapter, (
            f"{type(self).__module__}.{type(self).__name__}."
            f"orm_adapter must be set"
        )

    @property
    def signature_overrides(
        self,
    ) -> dict[type[ReplaceSignatureDependency], ReplaceSignatureDependency]:
        return {
            CreateSchemaDependency: CreateSchemaDependency(self.create_schema),
            UpdateSchemaDependency: UpdateSchemaDependency(self.update_schema),
            PublicSchemaDependency: PublicSchemaDependency(self.public_schema),
            PublicListSchemaDependency: PublicListSchemaDependency(
                self.public_list_schema),
            FilterSchemaDependency: FilterSchemaDependency(self.filter_schema),
            SortSchemaDependency: SortSchemaDependency(self.sort_schema),
            IncludeSchemaDependency: IncludeSchemaDependency(
                self.include_schema),
            PKFieldsDependency: PKFieldsDependency(self.pk_fields),
        } | self.dependency_overrides

    def override_dependencies(self, original_func: Callable):
        sig = inspect.signature(original_func)

        parameters = list(sig.parameters.values())
        new_parameters = []

        overrides = self.signature_overrides

        overrided_params: dict[str, ReplaceSignatureDependency] = {}


        for param in parameters:
            if (getattr(param.annotation, '__metadata__', None) is not None
                and len(param.annotation.__metadata__) > 0
            ):
                annotation = param.annotation.__metadata__[0]
            else:
                annotation = param.annotation

            if (
                inspect.isclass(annotation)
                and issubclass(annotation, (
                    ReplaceSignatureDependency
                ))
            ):
                try:
                    override = overrides[annotation]
                except KeyError as exc:
                    raise ValueError(
                        f"You need to add {annotation.__name__} "
                        f"to {type(self).__name__}'s dependency_overrides",
                    ) from exc
                new_params = override.get_new_params(param)
                new_parameters.extend(new_params)

                overrided_params[param.name] = override
            else:
                new_parameters.append(param)

        new_sig = inspect.Signature(parameters=new_parameters)

        @wraps(original_func)
        async def wrapper(**kwargs):
            for name, override in overrided_params.items():
                kwargs = override.pack_to_originals(name, **kwargs)
            return await original_func(**kwargs)

        wrapper.__signature__ = new_sig

        # Remove old annotations
        if overrided_params:
            wrapper.__annotations__ = {
                **get_type_hints(original_func),
                **{ p.name: p.annotation for p in new_parameters },
                }
            all_items = list(wrapper.__annotations__.keys())
            for item_name in all_items:
                if item_name not in new_parameters:
                    wrapper.__annotations__.pop(item_name, None)

        return wrapper

    def generate_unique_id(self, route: APIRoute) -> str:
        operation_id = f"{route.name}{route.path_format}"
        operation_id = re.sub(r"\W", "_", operation_id)
        assert route.methods
        operation_id = f"{operation_id}_{list(route.methods)[0].lower()}"
        operation_id = f"{operation_id}_{type(self.public_schema).__name__}"
        return operation_id

    @property
    def id_path(self):
        return ("/" + "/".join(
            [f'{{{n}}}' for n in self.pk_fields.model_fields.keys()])
        )

    def add_get_many_route(self, router: APIRouter):
        endpoint = self.override_dependencies(
            self.orm_adapter.get_many_handler,
        )
        if self.public_schema and not self.disable_get_many:
            router.add_api_route(
                "",
                endpoint,
                response_model = self.public_list_schema,
            )


    def add_get_one_route(self, router: APIRouter):
        endpoint = self.override_dependencies(self.orm_adapter.get_one_handler)
        if self.public_schema and not self.disable_get_one:
            router.add_api_route(
                self.id_path,
                endpoint,
                response_model = self.public_schema,
                generate_unique_id_function=self.generate_unique_id,
            )

    def add_create_one_route(self, router: APIRouter):
        endpoint = self.override_dependencies(
            self.orm_adapter.create_one_handler,
        )
        if self.create_schema and not self.disable_create:
            router.add_api_route(
                "",
                endpoint,
                methods=["POST"],
                response_model = self.create_out_schema,
            )

    def add_update_one_route(self, router: APIRouter):
        endpoint = self.override_dependencies(
            self.orm_adapter.update_one_handler,
        )
        if self.update_schema and not self.disable_update:
            router.add_api_route(
                self.id_path,
                endpoint,
                methods=["PATCH"],
                response_model = self.update_out_schema,
            )


    def add_delete_one_route(self, router: APIRouter):
        endpoint = self.override_dependencies(
            self.orm_adapter.delete_one_handler,
        )
        if  not self.disable_delete:
            router.add_api_route(
                self.id_path,
                endpoint,
                methods=["DELETE"],
                response_model = self.public_schema,
            )

    def get_router(self, **router_kwargs):
        self.verify_orm_adapter()
        self.router_kwargs.update(router_kwargs)
        router = APIRouter(**self.router_kwargs)

        self.add_get_many_route(router)
        self.add_get_one_route(router)
        self.add_create_one_route(router)
        self.add_update_one_route(router)
        self.add_delete_one_route(router)

        return router

class CRUDCollection(CRUDCollectionBase):
    pass
