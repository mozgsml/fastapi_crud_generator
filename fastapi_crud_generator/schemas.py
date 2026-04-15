from typing import Generic, TypeVar

from pydantic import BaseModel, Field

ListItemT = TypeVar('ListItemT')

class PaginatorPage(BaseModel, Generic[ListItemT]):
    page: int = Field(ge=1)
    per_page: int = Field(ge=1)
    count: int = Field(ge=0)
    data: list[ListItemT]


class Message(BaseModel):
    success: bool = True
    message: str
