from abc import ABC, abstractmethod


class ORMAdapterBase(ABC):

    @abstractmethod
    async def get_many_endpoint(self):
        pass

    @abstractmethod
    async def get_one_endpoint(self):
        pass

    @abstractmethod
    async def create_one_endpoint(self):
        pass

    @abstractmethod
    async def create_many_endpoint(self):
        pass

    @abstractmethod
    async def update_one_endpoint(self):
        pass

    @abstractmethod
    async def update_many_endpoint(self):
        pass

    @abstractmethod
    async def delete_one_endpoint(self):
        pass
