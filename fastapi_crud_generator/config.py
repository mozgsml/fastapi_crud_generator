from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, TypedDict

from fastapi.params import Depends


class RouterKwargs(TypedDict, total=False):
    """Typed subset of ``APIRouter.include_router`` keyword arguments."""

    tags: list[str]
    dependencies: Sequence[Depends]
    deprecated: bool
    include_in_schema: bool
    responses: dict[int | str, dict[str, Any]]


@dataclass
class NestedConfig:
    """Configuration for a nested collection.

    Passed as ``config`` to ``add_nested_collection``.

    ``router_kwargs`` accepts any ``APIRouter.include_router`` parameters
    (tags, dependencies, deprecated, include_in_schema, responses).
    """

    router_kwargs: RouterKwargs = field(default_factory=dict)


@dataclass(frozen=True)
class CRUDConfigDict:
    """Configuration for automatic CRUD schema generation.

    Place on a SQLModel table class as ``crud_config`` to control
    how the ORM adapter generates schemas and routes.

    Attributes:
        base_fields: Fields shared across schemas; used as a fallback
            when public_fields, create_fields or update_fields are not set.
        public_fields: Fields exposed in the public (GET) schema.
        create_fields: Fields accepted in the create (POST) schema.
        update_fields: Fields accepted in the update (PATCH) schema.

    """

    base_fields: set[str] = field(default_factory=set)
    public_fields: set[str] = field(default_factory=set)
    create_fields: set[str] = field(default_factory=set)
    update_fields: set[str] = field(default_factory=set)
