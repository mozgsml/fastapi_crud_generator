from abc import ABC, abstractmethod

from pydantic import BaseModel


class ORMAdapterBase(ABC):

    @abstractmethod
    def generate_public_schema(
        self,
        fields: set[str] | None = None,
        base_fields: set[str] | None = None,
    ) -> type[BaseModel]:
        pass

    @abstractmethod
    def generate_create_schema(
        self,
        fields: set[str] | None = None,
        base_fields: set[str] | None = None,
    ) -> type[BaseModel]:
        pass

    @abstractmethod
    def generate_update_schema(
        self,
        fields: set[str] | None = None,
        base_fields: set[str] | None = None,
    ) -> type[BaseModel]:
        pass

    @abstractmethod
    def generate_include_schema(self) -> type[BaseModel]:
        pass

    @abstractmethod
    async def get_many_handler(self):
        pass

    @abstractmethod
    async def get_one_handler(self):
        pass

    @abstractmethod
    async def create_one_handler(self):
        pass

    @abstractmethod
    async def create_many_handler(self):
        pass

    @abstractmethod
    async def update_one_handler(self):
        pass

    @abstractmethod
    async def update_many_handler(self):
        pass

    @abstractmethod
    async def delete_one_handler(self):
        pass
