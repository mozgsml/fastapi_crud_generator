# Dependencies

Стандартные FastAPI-зависимости (`Depends`) можно навешивать на все маршруты сразу
или на конкретный тип операции.

## На все маршруты

```python
from fastapi import Depends
from fastapi_crud_generator import CRUDCollection

crud = CRUDCollection(
    orm_adapter=adapter,
    dependencies=[Depends(require_auth)],
)
```

## На конкретный тип

```python
crud = CRUDCollection(
    orm_adapter=adapter,
    get_one_dependencies=[Depends(require_auth)],
    get_many_dependencies=[Depends(require_auth)],
    create_dependencies=[Depends(require_admin)],
    update_dependencies=[Depends(require_admin)],
    delete_dependencies=[Depends(require_admin)],
)
```

## Пример: JWT-авторизация

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def require_auth(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not verify_token(credentials.credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")

crud = CRUDCollection(
    orm_adapter=adapter,
    dependencies=[Depends(require_auth)],
)
```

## На уровне роутера

Зависимости можно задать и при подключении роутера, а не в `CRUDCollection`:

```python
app.include_router(
    crud.get_router(prefix="/articles"),
    dependencies=[Depends(require_auth)],
)
```
