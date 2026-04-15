from typing import Annotated

from fastapi import Depends, Query

from fastapi_crud_generator.schemas import PaginatorPage
from abc import abstractmethod, ABC

class PaginatorBase(ABC):
    limit: int = 20
    offset: int = 0
    page: int = 1
    per_page: int = 20

    def __init__(
        self,
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=0)
    ):
        self.page = page
        self.per_page = per_page
        self.calc_offset_limit()

    def set_page(self, page: int):
        self.page = page
        self.calc_offset_limit()

    def set_per_page(self, per_page: int):
        self.per_page = per_page
        self.calc_offset_limit()

    def calc_offset_limit(self):
        self.limit = self.per_page * self.page
        self.offset = (self.page - 1) * self.per_page
