"""ORM adapter for Tortoise ORM async models."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, create_model

from fastapi_crud_generator.config import CRUDConfigDict
from fastapi_crud_generator.orm.base import ORMAdapterBase
from fastapi_crud_generator.paginator import PaginatorBase
from fastapi_crud_generator.schemas import (
    NotFoundError,
    PaginatorPage,
    ParentNotFoundError,
    ParentRef,
)

try:
    from tortoise.contrib.pydantic import pydantic_model_creator
    from tortoise.fields.relational import (
        BackwardFKRelation,
        BackwardOneToOneRelation,
        ForeignKeyFieldInstance,
        ManyToManyFieldInstance,
        RelationalField,
    )
except ImportError:
    TORTOISE_INSTALLED = False
else:
    TORTOISE_INSTALLED = True


def _is_relation(field: Any) -> bool:
    if not TORTOISE_INSTALLED:
        return False
    return isinstance(
        field,
        (
            RelationalField,
            BackwardFKRelation,
            BackwardOneToOneRelation,
            ManyToManyFieldInstance,
        ),
    )


def _is_auto_generated(name: str, field: Any, meta: Any) -> bool:
    """Return True if auto-supplied (PK autoincrement, auto_now)."""
    if getattr(field, "pk", False) and getattr(field, "generated", False):
        return True
    if getattr(field, "auto_now_add", False):
        return True
    if getattr(field, "auto_now", False):
        return True
    return False


def _creator_schema(
    name: str,
    model: type,
    field_names: set[str],
    *,
    optional: bool = False,
) -> type[BaseModel]:
    """Build a Pydantic schema via Tortoise's pydantic_model_creator."""
    include = tuple(sorted(field_names))
    if optional:
        return pydantic_model_creator(
            model, name=name, include=include, optional=include,
        )
    return pydantic_model_creator(model, name=name, include=include)


class TortoisePaginator(PaginatorBase):
    async def paginate(
        self, queryset: Any, paginator: "TortoisePaginator",
    ) -> PaginatorPage:
        # Called as paginator.paginate(qs, paginator) from the adapter.
        count = await queryset.count()
        data = await queryset.offset(
            paginator.offset,
        ).limit(paginator.limit)
        return {
            "count": count,
            "page": paginator.page,
            "per_page": paginator.per_page,
            "data": list(data),
        }


class TortoiseAdapter(ORMAdapterBase):
    """ORM adapter for Tortoise ORM models.

    Tortoise uses a global connection pool (``Tortoise.init``), so unlike
    SQLAlchemy-based adapters there is no ``get_session`` factory. Pass the
    Tortoise model class directly.

    Composite primary keys are not supported by Tortoise; this adapter
    assumes a single ``pk`` field per model.

    Args:
        model: The Tortoise ORM model class.

    """

    model: type | None = None
    paginator_class = TortoisePaginator

    def __init__(self, *, model: type | None = None) -> None:
        if not TORTOISE_INSTALLED:
            raise ImportError("tortoise-orm is not installed")
        self.model = model or self.__class__.model
        if not self.model:
            raise ValueError("model is required")

    def get_model_name(self) -> str:
        return self.model.__name__.lower()

    def get_crud_config(self) -> CRUDConfigDict:
        return getattr(self.model, "crud_config", CRUDConfigDict())

    def get_pk_field_names(self) -> set[str]:
        pk_attr = self.model._meta.pk_attr
        return {pk_attr} if pk_attr else set()

    def _all_scalar_field_names(self) -> set[str]:
        """Return non-relation field names (including FK _id backing cols)."""
        return {
            name
            for name, field in self.model._meta.fields_map.items()
            if not _is_relation(field)
        }

    def get_default_public_fields(self) -> set[str]:
        return self._all_scalar_field_names()

    def get_server_generated_field_names(self) -> set[str]:
        meta = self.model._meta
        return {
            name
            for name, field in meta.fields_map.items()
            if _is_auto_generated(name, field, meta)
        }

    def _auto_pk_field_names(self) -> set[str]:
        """Return auto-generated PK names (integer autoincrement only)."""
        meta = self.model._meta
        result: set[str] = set()
        for name, field in meta.fields_map.items():
            if (
                getattr(field, "pk", False)
                and getattr(field, "generated", False)
            ):
                result.add(name)
        return result

    def get_default_create_fields(
        self,
        exclude_related: list[type] | None = None,
    ) -> set[str]:
        meta = self.model._meta
        auto = (
            self.get_server_generated_field_names()
            | self._auto_pk_field_names()
        )
        # Exclude FK backing cols that point to an excluded parent model.
        fk_to_exclude: set[str] = set()
        if exclude_related:
            exclude_tables = {
                m._meta.db_table for m in exclude_related
            }
            for name, field in meta.fields_map.items():
                if isinstance(field, ForeignKeyFieldInstance):
                    ref_model = field.related_model
                    if (
                        ref_model is not None
                        and ref_model._meta.db_table in exclude_tables
                    ):
                        # The backing column is `name + "_id"` in Tortoise
                        fk_to_exclude.add(f"{name}_id")
        return self._all_scalar_field_names() - auto - fk_to_exclude

    def get_default_update_fields(self) -> set[str]:
        excluded = (
            self.get_pk_field_names()
            | self.get_server_generated_field_names()
        )
        return self._all_scalar_field_names() - excluded

    def _effective_fields(
        self,
        fields: set[str] | None,
        base_fields: set[str] | None,
        default: set[str],
    ) -> set[str]:
        crud = self.get_crud_config()
        main = fields or (crud.public_fields or None)
        base = base_fields or (crud.base_fields or None)
        if main is None and base is None:
            return default
        return (main or set()) | (base or set())

    def _flat_public_schema(
        self,
        fields: set[str] | None = None,
        base_fields: set[str] | None = None,
    ) -> type[BaseModel]:
        effective = self._effective_fields(
            fields,
            base_fields,
            self.get_default_public_fields() | self.get_pk_field_names(),
        )
        return _creator_schema(
            f"{self.model.__name__}Public", self.model, effective,
        )

    def generate_public_schema(
        self,
        fields: set[str] | None = None,
        base_fields: set[str] | None = None,
    ) -> type[BaseModel]:
        base = self._flat_public_schema(fields, base_fields)
        meta = self.model._meta
        rel_fields: dict[str, tuple] = {}
        for rel_name in meta.fetch_fields:
            field = meta.fields_map.get(rel_name)
            if field is None:
                continue
            related_cls = getattr(field, "related_model", None)
            if related_cls is None:
                continue
            tmp = object.__new__(TortoiseAdapter)
            tmp.model = related_cls
            nested = tmp._flat_public_schema()
            is_many = isinstance(
                field,
                (BackwardFKRelation, ManyToManyFieldInstance),
            )
            field_type = list[nested] if is_many else nested
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
        crud = self.get_crud_config()
        main = fields or (crud.create_fields or None)
        base = base_fields or (crud.base_fields or None)
        if main is None and base is None:
            effective = self.get_default_create_fields(exclude_related)
        else:
            effective = (main or set()) | (base or set())
        return _creator_schema(
            f"{self.model.__name__}Create", self.model, effective,
        )

    def generate_update_schema(
        self,
        fields: set[str] | None = None,
        base_fields: set[str] | None = None,
    ) -> type[BaseModel]:
        crud = self.get_crud_config()
        main = fields or (crud.update_fields or None)
        base = base_fields or (crud.base_fields or None)
        if main is None and base is None:
            effective = self.get_default_update_fields()
        else:
            effective = (main or set()) | (base or set())
        return _creator_schema(
            f"{self.model.__name__}Update",
            self.model,
            effective,
            optional=True,
        )

    def generate_pk_schema(self) -> type[BaseModel]:
        return _creator_schema(
            f"{self.model.__name__}PK", self.model, self.get_pk_field_names(),
        )

    def generate_include_schema(self) -> type[BaseModel]:
        rel_names = tuple(self.model._meta.fetch_fields)
        if not rel_names:
            return create_model(f"{self.model.__name__}Include")
        literal_type = Literal.__getitem__(rel_names)
        return create_model(
            f"{self.model.__name__}Include",
            include=(list[literal_type] | None, None),
        )

    def _get_rel_value(self, instance: Any, rel_name: str) -> Any:
        """Extract a loaded relation value, or None if not fetched.

        Tortoise descriptors always return either a ``ReverseRelation`` object
        (for reverse/M2M relations) or a ``QuerySet`` (for un-prefetched FK).
        We inspect the internal state to distinguish loaded from not-loaded.
        """
        from tortoise.queryset import QuerySet as TortoiseQS

        val = getattr(instance, rel_name, None)
        if val is None:
            return None
        # ReverseRelation / M2M — has _fetched flag
        if hasattr(val, "_fetched"):
            return val.related_objects if val._fetched else None
        # FK / OneToOne — QuerySet means not prefetched
        if isinstance(val, TortoiseQS):
            return None
        return val

    def _instance_to_dict(
        self,
        instance: Any,
        requested: set[str] | None = None,
    ) -> dict:
        """Convert a Tortoise instance to a plain dict for serialization.

        Requested relation fields carry their loaded values (list or object);
        all other relation fields are ``None``.
        """
        meta = self.model._meta
        result: dict = {}
        for name, field in meta.fields_map.items():
            if not _is_relation(field):
                result[name] = getattr(instance, name, None)
        for rel_name in meta.fetch_fields:
            if requested is not None and rel_name in requested:
                result[rel_name] = self._get_rel_value(instance, rel_name)
            else:
                result[rel_name] = None
        return result

    def _build_parent_filter(
        self, parent_refs: list[ParentRef],
    ) -> dict[str, Any]:
        """Translate parent refs into Tortoise filter kwargs."""
        filters: dict[str, Any] = {}
        for ref in parent_refs:
            parent_model = ref.model
            for name, field in self.model._meta.fields_map.items():
                if not isinstance(field, ForeignKeyFieldInstance):
                    continue
                if field.related_model is parent_model:
                    pk_name = parent_model._meta.pk_attr
                    pk_val = getattr(
                        ref.pk_values, pk_name, None,
                    )
                    if pk_val is not None:
                        filters[f"{name}_id"] = pk_val
        return filters

    def _parent_filter_str(
        self, parent_refs: list[ParentRef],
    ) -> dict[str, Any]:
        """Return filter dict for scoping to the parent chain.

        Handles two cases:
        - Direct FK: current model has a FK pointing to the parent model
          → filter by ``{fk_name}_id = pk_val``
        - Reverse FK: parent model has a FK pointing to the current model
          → use Tortoise reverse-relation path ``{rel_name}__pk = pk_val``
        """
        filters: dict[str, Any] = {}
        for ref in parent_refs:
            parent_model = ref.model
            pk_attr = parent_model._meta.pk_attr
            pk_val = getattr(ref.pk_values, pk_attr, None)
            # Direct FK (current model → parent)
            for fname, field in self.model._meta.fields_map.items():
                if (
                    isinstance(field, ForeignKeyFieldInstance)
                    and field.related_model is parent_model
                ):
                    filters[f"{fname}_id"] = pk_val
                    break
            else:
                # Reverse FK: parent model FK → current model
                # Use Tortoise ORM path: rel_name__pk_attr = pk_val
                for rel_name in self.model._meta.fetch_fields:
                    rfield = self.model._meta.fields_map.get(rel_name)
                    if (
                        rfield is not None
                        and isinstance(rfield, BackwardFKRelation)
                        and rfield.related_model is parent_model
                    ):
                        filters[f"{rel_name}__{pk_attr}"] = pk_val
                        break
        return filters

    async def _verify_parent_exists(
        self, parent_refs: list[ParentRef],
    ) -> bool:
        """Return True if the direct parent exists in the ancestor chain."""
        direct = parent_refs[0]
        parent_cls = direct.model
        pk_attr = parent_cls._meta.pk_attr
        pk_val = getattr(direct.pk_values, pk_attr, None)
        qs = parent_cls.filter(**{pk_attr: pk_val})
        # Scope to grandparent if present.
        if len(parent_refs) > 1:
            grandparent_filters = TortoiseAdapter(
                model=parent_cls,
            )._parent_filter_str(parent_refs[1:])
            qs = qs.filter(**grandparent_filters)
        return await qs.exists()

    async def get_one(
        self,
        pk_values: BaseModel,
        include_data: BaseModel,
        parent_refs: list[ParentRef] | None = None,
    ) -> Any | None:
        requested = set(getattr(include_data, "include", None) or [])
        filters = pk_values.model_dump()
        if parent_refs:
            filters.update(self._parent_filter_str(parent_refs))
        qs = self.model.filter(**filters)
        if requested:
            qs = qs.prefetch_related(*requested)
        instance = await qs.first()
        if instance is None:
            return None
        return self._instance_to_dict(instance, requested)

    async def get_many(
        self,
        filter_data: BaseModel,
        sort_data: BaseModel,
        include_data: BaseModel,
        paginator: TortoisePaginator,
        parent_refs: list[ParentRef] | None = None,
    ) -> PaginatorPage:
        requested = set(getattr(include_data, "include", None) or [])
        qs = self.model.all()
        if parent_refs:
            qs = qs.filter(**self._parent_filter_str(parent_refs))
        # Filter
        for key, value in filter_data.model_dump(exclude_unset=True).items():
            qs = qs.filter(**{key: value})
        # Sort
        sort_fields = type(sort_data).model_fields
        if len(sort_fields) == 1:
            sort_dict = sort_data.model_dump(exclude_unset=True)
            if sort_dict:
                sort_value = next(iter(sort_dict.values()))
                if not isinstance(sort_value, list):
                    sort_value = [sort_value]
                order_cols: list[str] = []
                seen: set[str] = set()
                for v in sort_value:
                    field, *direction = v.split(":", 2)
                    if field not in seen:
                        seen.add(field)
                        is_desc = direction and direction[0] == "desc"
                        prefix = "-" if is_desc else ""
                        order_cols.append(f"{prefix}{field}")
                if order_cols:
                    qs = qs.order_by(*order_cols)
        if requested:
            qs = qs.prefetch_related(*requested)
        page = await paginator.paginate(qs, paginator)
        page["data"] = [
            self._instance_to_dict(item, requested) for item in page["data"]
        ]
        return page

    async def create_one(
        self,
        data: BaseModel,
        parent_refs: list[ParentRef] | None = None,
    ) -> Any:
        data_dict = data.model_dump()
        if parent_refs:
            if not await self._verify_parent_exists(parent_refs):
                raise ParentNotFoundError
            for ref in parent_refs:
                parent_cls = ref.model
                pk_attr = parent_cls._meta.pk_attr
                pk_val = getattr(ref.pk_values, pk_attr, None)
                for fname, field in self.model._meta.fields_map.items():
                    if (
                        isinstance(field, ForeignKeyFieldInstance)
                        and field.related_model is parent_cls
                    ):
                        data_dict[f"{fname}_id"] = pk_val
        instance = await self.model.create(**data_dict)
        return self._instance_to_dict(instance)

    async def update_one(
        self,
        pk_values: BaseModel,
        data: BaseModel,
        parent_refs: list[ParentRef] | None = None,
    ) -> None:
        filters = pk_values.model_dump()
        if parent_refs:
            filters.update(self._parent_filter_str(parent_refs))
        exists = await self.model.filter(**filters).exists()
        if not exists:
            raise NotFoundError
        new_values = data.model_dump(exclude_unset=True)
        await self.model.filter(**filters).update(**new_values)

    async def delete_one(
        self,
        pk_values: BaseModel,
        parent_refs: list[ParentRef] | None = None,
    ) -> Any | None:
        filters = pk_values.model_dump()
        if parent_refs:
            filters.update(self._parent_filter_str(parent_refs))
        instance = await self.model.filter(**filters).first()
        if instance is None:
            return None
        await instance.delete()
        return self._instance_to_dict(instance)
