from abc import ABC, abstractmethod


class ORMAdapterBase(ABC):

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
