"""Router strategies — encapsulate nesting context for CRUD route building.

Each strategy carries the full ancestor context for one level of nesting:
- ``ancestor_names``: pk path-params contributed by ancestors, which the
  collection excludes from its own id_path so they are not repeated
- which dependency overrides to apply (ParentPKFieldsDependency chain)

``TopLevelStrategy`` is the default for standalone collections.
``NestedStrategy`` is produced by ``TopLevelStrategy.descend()`` and
further ``NestedStrategy.descend()`` calls as the router tree is built.
"""
import inspect
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel

from fastapi_crud_generator.deps import (
    ConstantDependency,
    ParentPKFieldsDependency,
    ReplaceSignatureDependency,
)

if TYPE_CHECKING:
    from fastapi_crud_generator.orm.base import ORMAdapterBase

_DUMMY_PARAM = inspect.Parameter("_", inspect.Parameter.POSITIONAL_OR_KEYWORD)


class RouterStrategy(ABC):
    """Context object for one level of the CRUD router tree."""

    # pk path-param names already bound by ancestors; a collection hands
    # this to get_id_path so it drops params an ancestor already placed
    # in the URL. Each concrete strategy sets it.
    ancestor_names: frozenset[str]

    @abstractmethod
    def get_overrides(
        self, resolved_overrides: dict,
    ) -> dict[type[ReplaceSignatureDependency], ReplaceSignatureDependency]:
        """Return the full overrides dict for this level."""

    @abstractmethod
    def get_child_strategy(
        self,
        pk_dep: ReplaceSignatureDependency,
        model: type,
    ) -> "RouterStrategy":
        """Return the strategy for the next (child) nesting level."""

    def get_create_schema(
        self,
        orm_adapter: "ORMAdapterBase",
        fields: set[str] | None,
        base_fields: set[str] | None,
    ) -> type[BaseModel]:
        """Generate a create schema appropriate for this routing context."""
        return orm_adapter.generate_create_schema(fields, base_fields)


class TopLevelStrategy(RouterStrategy):
    """Strategy for a standalone (non-nested) collection."""

    ancestor_names = frozenset()

    def get_overrides(self, resolved_overrides: dict) -> dict:
        return resolved_overrides

    def get_child_strategy(
        self, pk_dep: ReplaceSignatureDependency, model: type,
    ) -> "NestedStrategy":
        """Return strategy for the first child nesting level."""
        parent_dep = ParentPKFieldsDependency(
            base_dep=pk_dep,
            model=model,
            parent_dep=ConstantDependency([]),
        )
        ancestor_names = frozenset(
            p.name for p in parent_dep.get_new_params(_DUMMY_PARAM)
        )
        return NestedStrategy(
            ancestor_names=ancestor_names,
            parent_dep=parent_dep,
        )


class NestedStrategy(RouterStrategy):
    """Strategy for a collection nested under one or more parents."""

    def __init__(
        self,
        ancestor_names: frozenset[str],
        parent_dep: ParentPKFieldsDependency,
    ) -> None:
        self.ancestor_names = ancestor_names
        self._parent_dep = parent_dep

    def get_overrides(self, resolved_overrides: dict) -> dict:
        return {
            **resolved_overrides,
            ParentPKFieldsDependency: self._parent_dep,
        }

    def get_child_strategy(
        self, pk_dep: ReplaceSignatureDependency, model: type,
    ) -> "NestedStrategy":
        """Return strategy for the next child nesting level."""
        new_dep = ParentPKFieldsDependency(
            base_dep=pk_dep,
            model=model,
            parent_dep=self._parent_dep,
        )
        new_names = self.ancestor_names | frozenset(
            p.name for p in new_dep.get_new_params(_DUMMY_PARAM)
        )
        return NestedStrategy(ancestor_names=new_names, parent_dep=new_dep)

    def get_create_schema(
        self,
        orm_adapter: "ORMAdapterBase",
        fields: set[str] | None,
        base_fields: set[str] | None,
    ) -> type[BaseModel]:
        """Exclude FK+PK fields pointing to the direct parent model."""
        return orm_adapter.generate_create_schema(
            fields, base_fields,
            exclude_related=[self._parent_dep.parent_model],
        )
