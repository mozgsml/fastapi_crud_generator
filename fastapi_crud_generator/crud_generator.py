import inspect
import re
from abc import ABC
from collections.abc import Callable
from functools import wraps
from typing import Annotated, Any, get_type_hints

from fastapi import APIRouter, Depends, HTTPException
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field, create_model

from fastapi_crud_generator.config import NestedConfig
from fastapi_crud_generator.deps import (
    ConstantDependency,
    CreateSchemaDependency,
    FilterSchemaDependency,
    IncludeSchemaDependency,
    PaginatorDependency,
    ParentPKFieldsDependency,
    PKFieldsDependency,
    PublicListSchemaDependency,
    PublicSchemaDependency,
    ReplaceSignatureDependency,
    ReplaceWithAnnotationDependency,
    SortSchemaDependency,
    UpdateSchemaDependency,
)
from fastapi_crud_generator.orm.base import ORMAdapterBase
from fastapi_crud_generator.paginator import PaginatorBase
from fastapi_crud_generator.schemas import (
    NotFoundError,
    PaginatorPage,
    ParentNotFoundError,
)
from fastapi_crud_generator.strategies import RouterStrategy, TopLevelStrategy
from fastapi_crud_generator.utils import (
    create_filter_model,
    create_sort_schema,
)

_DEFAULT_STRATEGY: RouterStrategy = TopLevelStrategy()


def _init_list_param(
    param: list | None,
    class_default: list | None,
) -> list:
    """Return param if provided, else fall back to class_default or []."""
    return param if param is not None else (class_default or [])


class CRUDCollectionBase(ABC):
    """Base class for CRUD route collections.

    Subclass this (or ``CRUDCollection``) to create a set of CRUD endpoints
    for a given ORM adapter. Override handler methods or class attributes to
    customise behaviour without touching routing or dependency wiring.
    """

    orm_adapter: ORMAdapterBase | None = None

    public_schema: BaseModel = None
    public_list_schema: BaseModel = None

    update_schema: BaseModel = None
    update_out_schema = Any

    create_schema: BaseModel = None
    create_out_schema = Any

    pk_fields: type[BaseModel] | None = None

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
        ReplaceSignatureDependency | Any,
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

        pk_fields: type[BaseModel] | None = None,

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
            ReplaceSignatureDependency | Any,
        ] | None = None,

        **router_kwargs: dict,

    ):
        """Initialise the collection, resolving schemas and dependencies."""
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
        self.create_schema = create_schema or self.create_schema
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
        self.pk_fields = (
            pk_fields or self.pk_fields
            or self.apply_pk_aliases(
                self.orm_adapter.generate_pk_schema(),
            )
        )
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
        self._nested_collections: list[
            tuple[str, CRUDCollectionBase]
        ] = []


    def apply_pk_aliases(
        self, pk_schema: type[BaseModel],
    ) -> type[BaseModel]:
        """Return pk_schema with model-name-prefixed aliases on plain fields.

        Fields whose names contain no underscore get an alias
        ``{model_name}_{field}`` (e.g. ``id`` → ``user_id``).
        Override to customise aliasing behaviour.
        """
        model_name = self.orm_adapter.get_model_name()
        if not model_name:
            return pk_schema
        field_defs = {}
        for name, info in pk_schema.model_fields.items():
            alias = name if "_" in name else f"{model_name}_{name}"
            field_defs[name] = (
                info.annotation, Field(validation_alias=alias),
            )
        return create_model(pk_schema.__name__, **field_defs)

    def verify_orm_adapter(self) -> None:
        """Raise if orm_adapter is not set."""
        if not self.orm_adapter:
            msg = (
                f"{type(self).__module__}.{type(self).__name__}."
                f"orm_adapter must be set"
            )
            raise ValueError(msg)

    def get_resolved_overrides(
        self,
        strategy: RouterStrategy | None = None,
    ) -> dict[type[ReplaceSignatureDependency], ReplaceSignatureDependency]:
        """Merge default overrides with user-supplied dependency_overrides."""
        strategy = strategy or _DEFAULT_STRATEGY
        create_schema = self.create_schema or strategy.get_create_schema(
            self.orm_adapter, self.create_fields, self.base_fields,
        )
        defaults = {
            CreateSchemaDependency: CreateSchemaDependency(create_schema),
            UpdateSchemaDependency: UpdateSchemaDependency(self.update_schema),
            PublicSchemaDependency: PublicSchemaDependency(self.public_schema),
            PublicListSchemaDependency: PublicListSchemaDependency(
                self.public_list_schema),
            FilterSchemaDependency: FilterSchemaDependency(self.filter_schema),
            SortSchemaDependency: SortSchemaDependency(self.sort_schema),
            IncludeSchemaDependency: IncludeSchemaDependency(
                self.include_schema),
            PKFieldsDependency: PKFieldsDependency(self.pk_fields),
            PaginatorDependency: PaginatorDependency(
                self.orm_adapter.paginator_class,
            ),
            ParentPKFieldsDependency: ConstantDependency([]),
        }
        for key, val in self.dependency_overrides.items():
            defaults[key] = (
                val if isinstance(val, ReplaceSignatureDependency)
                else ReplaceWithAnnotationDependency(val)
            )
        return defaults

    def override_dependencies(  # noqa: C901
        self,
        original_func: Callable,
        overrides: dict | None = None,
    ) -> Callable:
        """Replace marker annotations in a handler's signature with real DI."""
        sig = inspect.signature(original_func)

        parameters = list(sig.parameters.values())
        new_parameters = []
        seen_names: set[str] = set()

        if overrides is None:
            overrides = self.get_resolved_overrides()

        overrided_params: dict[str, ReplaceSignatureDependency] = {}

        for param in parameters:
            if (getattr(param.annotation, "__metadata__", None) is not None
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
                if annotation not in overrides:
                    msg = (
                        f"You need to add {annotation.__name__} "
                        f"to {type(self).__name__}'s dependency_overrides"
                    )
                    raise ValueError(msg)
                override = overrides[annotation]
                fresh_params = [
                    p for p in override.get_new_params(param)
                    if p.name not in seen_names
                ]
                seen_names.update(p.name for p in fresh_params)
                new_parameters.extend(fresh_params)
                overrided_params[param.name] = override
            elif param.name not in seen_names:
                seen_names.add(param.name)
                new_parameters.append(param)

        new_sig = inspect.Signature(parameters=new_parameters)
        handler_params = set(sig.parameters)

        @wraps(original_func)
        async def wrapper(**kwargs):
            raw_kwargs = dict(kwargs)
            for name, override in overrided_params.items():
                kwargs[name] = override.pack_to_originals(name, **raw_kwargs)
            kwargs = {k: v for k, v in kwargs.items() if k in handler_params}
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

    async def get_one_handler(
        self,
        pk_field_values: Annotated[BaseModel, PKFieldsDependency],
        include_data: Annotated[BaseModel, IncludeSchemaDependency],
        parent_refs: Annotated[list, ParentPKFieldsDependency],
    ) -> object:
        """Return a single object or call get_one_not_found if missing."""
        result = await self.orm_adapter.get_one(
            pk_field_values, include_data, parent_refs=parent_refs,
        )
        if result is None:
            return await self.get_one_not_found(pk_field_values, include_data)
        return result

    async def get_one_not_found(
        self, _pk_field_values: BaseModel, _include_data: BaseModel,
    ) -> object:
        """Raise 404 by default; override to customise not-found behavior."""
        raise HTTPException(status_code=404, detail="Not found")

    async def get_many_handler(
        self,
        paginator: Annotated[PaginatorBase, PaginatorDependency],
        filter_data: Annotated[BaseModel, FilterSchemaDependency],
        sort_data: Annotated[BaseModel, SortSchemaDependency],
        include_data: Annotated[BaseModel, IncludeSchemaDependency],
        parent_refs: Annotated[list, ParentPKFieldsDependency],
    ) -> object:
        """Handle GET / — return a paginated, filtered, sorted list."""
        return await self.orm_adapter.get_many(
            filter_data, sort_data, include_data, paginator,
            parent_refs=parent_refs,
        )

    async def create_one_handler(
        self,
        create_data: Annotated[BaseModel, CreateSchemaDependency],
        parent_refs: Annotated[list, ParentPKFieldsDependency],
    ) -> object:
        """Handle POST / — persist a new object and return it."""
        try:
            return await self.orm_adapter.create_one(
                create_data, parent_refs=parent_refs,
            )
        except ParentNotFoundError as exc:
            raise HTTPException(
                status_code=404, detail="Parent not found",
            ) from exc

    async def update_one_handler(
        self,
        pk_field_values: Annotated[BaseModel, PKFieldsDependency],
        update_data: Annotated[BaseModel, UpdateSchemaDependency],
        parent_refs: Annotated[list, ParentPKFieldsDependency],
    ) -> None:
        """Handle PATCH /{pk} — partially update an existing object."""
        try:
            await self.orm_adapter.update_one(
                pk_field_values, update_data, parent_refs=parent_refs,
            )
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc

    async def delete_one_handler(
        self,
        pk_field_values: Annotated[BaseModel, PKFieldsDependency],
        parent_refs: Annotated[list, ParentPKFieldsDependency],
    ) -> object:
        """Handle DELETE /{pk} — delete an object by primary key."""
        result = await self.orm_adapter.delete_one(
            pk_field_values, parent_refs=parent_refs,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Not found")
        return result

    def generate_unique_id(self, route: APIRoute) -> str:
        """Build a unique OpenAPI operation ID from name, path and method."""
        if not route.methods:
            msg = f"Route {route.name!r} has no HTTP methods defined"
            raise ValueError(msg)
        operation_id = re.sub(r"\W", "_", f"{route.name}{route.path_format}")
        method = next(iter(route.methods)).lower()
        return f"{operation_id}_{method}_{type(self.public_schema).__name__}"

    def get_id_path(self, exclude: frozenset[str] = frozenset()) -> str:
        """URL path segment for single-object endpoints, e.g. /{user_id}.

        ``exclude`` drops pk params already bound by an ancestor's path,
        so a nested collection does not repeat them. Override this to
        pin a fixed segment (e.g. ``return "/me"`` for a token-scoped
        singleton, where the identity comes from auth, not the URL).
        """
        return "/" + "/".join(
            f"{{{f.validation_alias or n}}}"
            for n, f in self.pk_fields.model_fields.items()
            if (f.validation_alias or n) not in exclude
        )

    def add_get_many_route(
        self, router: APIRouter, strategy: RouterStrategy | None = None,
    ) -> None:
        """Register GET / on the router."""
        strategy = strategy or _DEFAULT_STRATEGY
        overrides = strategy.get_overrides(self.get_resolved_overrides(strategy))
        if self.public_schema and not self.disable_get_many:
            router.add_api_route(
                "",
                self.override_dependencies(self.get_many_handler, overrides),
                response_model=self.public_list_schema,
                dependencies=self.get_many_dependencies,
            )

    def add_get_one_route(
        self, router: APIRouter, strategy: RouterStrategy | None = None,
    ) -> None:
        """Register GET /{pk} on the router."""
        strategy = strategy or _DEFAULT_STRATEGY
        overrides = strategy.get_overrides(self.get_resolved_overrides(strategy))
        if self.public_schema and not self.disable_get_one:
            router.add_api_route(
                self.get_id_path(strategy.ancestor_names),
                self.override_dependencies(self.get_one_handler, overrides),
                response_model=self.public_schema,
                generate_unique_id_function=self.generate_unique_id,
                dependencies=self.get_one_dependencies,
            )

    def add_create_one_route(
        self, router: APIRouter, strategy: RouterStrategy | None = None,
    ) -> None:
        """Register POST / on the router."""
        strategy = strategy or _DEFAULT_STRATEGY
        overrides = strategy.get_overrides(self.get_resolved_overrides(strategy))
        if not self.disable_create:
            router.add_api_route(
                "",
                self.override_dependencies(
                    self.create_one_handler, overrides,
                ),
                methods=["POST"],
                response_model=self.create_out_schema,
                dependencies=self.create_dependencies,
                responses={404: {"description": "Parent not found"}},
            )

    def add_update_one_route(
        self, router: APIRouter, strategy: RouterStrategy | None = None,
    ) -> None:
        """Register PATCH /{pk} on the router."""
        strategy = strategy or _DEFAULT_STRATEGY
        overrides = strategy.get_overrides(self.get_resolved_overrides(strategy))
        if self.update_schema and not self.disable_update:
            router.add_api_route(
                self.get_id_path(strategy.ancestor_names),
                self.override_dependencies(
                    self.update_one_handler, overrides,
                ),
                methods=["PATCH"],
                response_model=self.update_out_schema,
                dependencies=self.update_dependencies,
            )

    def add_delete_one_route(
        self, router: APIRouter, strategy: RouterStrategy | None = None,
    ) -> None:
        """Register DELETE /{pk} on the router."""
        strategy = strategy or _DEFAULT_STRATEGY
        overrides = strategy.get_overrides(self.get_resolved_overrides(strategy))
        if not self.disable_delete:
            router.add_api_route(
                self.get_id_path(strategy.ancestor_names),
                self.override_dependencies(
                    self.delete_one_handler, overrides,
                ),
                methods=["DELETE"],
                response_model=self.public_schema,
                dependencies=self.delete_dependencies,
            )

    def add_nested_collection(
        self,
        path: str,
        child: "CRUDCollectionBase",
        config: NestedConfig | None = None,
    ) -> None:
        """Register child as a nested collection under this collection."""
        self._nested_collections.append(
            (path, child, config or NestedConfig()),
        )

    def get_router(
        self,
        strategy: RouterStrategy | None = None,
        **router_kwargs: object,
    ) -> APIRouter:
        """Build and return an APIRouter with all enabled CRUD routes."""
        strategy = strategy or _DEFAULT_STRATEGY
        self.verify_orm_adapter()
        effective_kwargs = {**self.router_kwargs, **router_kwargs}
        router = APIRouter(**effective_kwargs)

        self.add_get_many_route(router, strategy)
        self.add_get_one_route(router, strategy)
        self.add_create_one_route(router, strategy)
        self.add_update_one_route(router, strategy)
        self.add_delete_one_route(router, strategy)

        if self._nested_collections:
            overrides = strategy.get_overrides(self.get_resolved_overrides(strategy))
            child_strategy = strategy.get_child_strategy(
                pk_dep=overrides[PKFieldsDependency],
                model=self.orm_adapter.model,
            )
            id_path = self.get_id_path(strategy.ancestor_names)
            for path, child, cfg in self._nested_collections:
                prefix = id_path.rstrip("/") + "/" + path.lstrip("/")
                router.include_router(
                    child.get_router(strategy=child_strategy),
                    prefix=prefix,
                    **cfg.router_kwargs,
                )

        return router

class CRUDCollection(CRUDCollectionBase):
    """Concrete CRUD collection — subclass and set orm_adapter to use."""
