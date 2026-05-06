import types
from enum import Enum
from typing import Annotated, Literal, Optional, Union, get_args, get_origin

from fastapi.params import Query
from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo

acepted_tupes = (int, float, str, bool, Enum)


def has_none_in_annotation(annotation: type) -> bool:
    """Return True if annotation already includes None."""
    origin = get_origin(annotation)
    if origin is Union:
        return type(None) in get_args(annotation)
    if isinstance(annotation, types.UnionType):
        return type(None) in get_args(annotation)
    return False


def make_pydantic_field(
    field_info: FieldInfo,
    *,
    optional: bool = False,
    exclude_metadata: tuple[type, ...] = (),
) -> tuple[type, FieldInfo]:
    """Build an (annotation, FieldInfo) pair from a FieldInfo object.

    Strips any metadata types listed in exclude_metadata (e.g. ORM-specific
    annotations). When optional=True, wraps annotation with None and resets
    the default to None so the field is never required.
    """
    field_dict = field_info.asdict()
    annotation = field_dict['annotation']
    metadata = [m for m in field_dict['metadata']
                if not isinstance(m, exclude_metadata)]
    attributes = dict(field_dict['attributes'])

    if optional:
        annotation = Union[annotation, None]
        attributes['default'] = None
        attributes['default_factory'] = None

    new_field_info = Field(**attributes)
    annotated_type = Annotated[annotation, *metadata] if metadata else annotation
    return (annotated_type, new_field_info)

def to_optional_fields(
    source_model: type[BaseModel],
    *,
    exclude_metadata: tuple[type, ...] = (),
) -> dict[str, tuple]:
    """Return create_model field definitions with every field made optional."""
    return {
        name: make_pydantic_field(
            field_info, optional=True, exclude_metadata=exclude_metadata,
        )
        for name, field_info in source_model.model_fields.items()
    }


def slice_model(
    model_name: str,
    source_model: type[BaseModel],
    *,
    fields: set[str] | None = None,
    optional: bool = False,
    exclude_metadata: tuple[type, ...] = (),
) -> type[BaseModel]:
    """Create a Pydantic model from a subset of source_model fields."""
    field_defs = {
        name: make_pydantic_field(
            field_info, optional=optional, exclude_metadata=exclude_metadata,
        )
        for name, field_info in source_model.model_fields.items()
        if fields is None or name in fields
    }
    return create_model(model_name, **field_defs)


def create_filter_model(
    public_model: BaseModel,
    accepted_types: list[type] | tuple[type] = acepted_tupes,
) -> BaseModel:
    """Build a Pydantic filter model from the public model's scalar fields.

    Includes only fields whose type is one of accepted_types (int, float,
    str, bool, Enum by default). All fields become optional query params.
    """
    accepted_types = tuple(accepted_types)
    fields = {}
    for name, info in public_model.model_fields.items():
        annotation = Optional[info.annotation]
        args = get_args(annotation)
        if (isinstance(args[0], type)
            and issubclass(args[0], accepted_types)
            and args[1] is type(None)
            and len(args) == 2
        ):
            fields[name] = (annotation, None)

    return create_model(f"{public_model.__name__}Filter", **fields)


def create_sort_schema(
    public_model: BaseModel,
    accepted_types: list[type] | tuple[type] = acepted_tupes,
) -> BaseModel:
    """Build a Pydantic sort schema from the public model's scalar fields.

    For each accepted field generates three Literal values: ``field``,
    ``field:asc``, ``field:desc``. The result is a model with a single
    optional ``sort`` query parameter accepting a list of those values.
    """
    accepted_types = tuple(accepted_types)
    fields_names = []
    for name, info in public_model.model_fields.items():
        annotation = Optional[info.annotation]
        args = get_args(annotation)
        if (isinstance(args[0], type)
            and issubclass(args[0], accepted_types)
            and args[1] is type(None)
            and len(args) == 2
        ):
            fields_names.append(name)
            fields_names.append(f'{name}:asc')
            fields_names.append(f'{name}:desc')

    literal_type = Literal.__getitem__(tuple(fields_names))

    result = create_model(
        f"{public_model.__name__}Sort",
        sort=(Annotated[Optional[list[literal_type]], Query()], None),
    )
    return result
