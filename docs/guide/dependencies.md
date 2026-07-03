# Dependencies

Standard FastAPI dependencies (`Depends`) can be applied to all routes at once
or to a specific operation type.

## All routes

```python
from fastapi import Depends
from fastapi_crud_generator import CRUDCollection

crud = CRUDCollection(
    orm_adapter=adapter,
    dependencies=[Depends(require_auth)],
)
```

## Per operation type

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

## Example: JWT authentication

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

## At router level

Dependencies can also be added when mounting the router rather than in `CRUDCollection`:

```python
app.include_router(
    crud.get_router(prefix="/articles"),
    dependencies=[Depends(require_auth)],
)
```
