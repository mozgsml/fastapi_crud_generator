from abc import ABC, abstractmethod

from fastapi import Query

from fastapi_crud_generator.schemas import PaginatorPage


class PaginatorBase(ABC):
    """Base class for paginators injected as FastAPI dependencies.

    Subclass and implement ``paginate`` to provide ORM-specific
    query execution. ``page`` and ``per_page`` are read from query
    parameters automatically.
    """

    limit: int = 20
    offset: int = 0
    page: int = 1
    per_page: int = 20

    def __init__(  # noqa: D107
        self,
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=0),
    ) -> None:
        self.page = page
        self.per_page = per_page
        self.calc_offset_limit()

    def set_page(self, page: int) -> None:
        """Set current page and recalculate limit/offset."""
        self.page = page
        self.calc_offset_limit()

    def set_per_page(self, per_page: int) -> None:
        """Set page size and recalculate limit/offset."""
        self.per_page = per_page
        self.calc_offset_limit()

    def calc_offset_limit(self) -> None:
        """Recalculate limit and offset from current page and per_page."""
        self.limit = self.per_page
        self.offset = (self.page - 1) * self.per_page

    @abstractmethod
    async def paginate(self) -> PaginatorPage:
        """Execute the query and return a paginated result page."""
