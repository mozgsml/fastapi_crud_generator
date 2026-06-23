from dataclasses import dataclass
from types import ModuleType
from typing import Callable

POSTGRES_URL_ENV = "POSTGRES_URL"
MYSQL_URL_ENV = "MYSQL_URL"


@dataclass
class BackendContext:
    make_adapter: Callable
    models: ModuleType
