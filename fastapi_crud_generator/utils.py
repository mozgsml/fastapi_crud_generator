from enum import Enum
from typing import Annotated, Literal, Optional, get_args

from fastapi.params import Query
from pydantic import BaseModel, create_model

acepted_tupes = (int, float, str, bool, Enum)

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
