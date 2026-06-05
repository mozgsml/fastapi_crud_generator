from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

ListItemT = TypeVar('ListItemT')
ModelT = TypeVar('ModelT')

class PaginatorPage(BaseModel, Generic[ListItemT]):
    page: int = Field(ge=1)
    per_page: int = Field(ge=1)
    count: int = Field(ge=0)
    data: list[ListItemT]


class Message(BaseModel):
    success: bool = True
    message: str


@dataclass
class ParentRef(Generic[ModelT]):
    """Reference to a parent collection item in a nested route.

    Passed to ORM adapter methods so they can filter, set foreign keys,
    or verify ownership relative to the parent object.

    Attributes:
        model: The parent's ORM model class (e.g. ``User``).
        pk_values: The parent's primary key values parsed from the URL.

    """

    model: type[ModelT]
    pk_values: BaseModel
