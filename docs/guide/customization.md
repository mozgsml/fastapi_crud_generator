# Customization

## Disabling endpoints

```python
crud = CRUDCollection(
    orm_adapter=adapter,
    disable_delete=True,
    disable_create=True,
)
```

## Overriding handlers via subclass

Subclass `CRUDCollection` and override the methods you need:

```python
from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter

class ArticleCRUD(CRUDCollection):
    orm_adapter = SQLModelAdapter(model=Article, get_session=get_session)

    async def get_one_not_found(self, pk_values, include_data):
        raise HTTPException(status_code=404, detail="Article not found")

    async def create_one_handler(self, create_data, parent_refs):
        create_data.slug = slugify(create_data.title)
        return await super().create_one_handler(create_data, parent_refs)

crud = ArticleCRUD()
app.include_router(crud.get_router(prefix="/articles"))
```

## Class attributes instead of constructor arguments

All `CRUDCollection` parameters can be set as class attributes:

```python
class ArticleCRUD(CRUDCollection):
    orm_adapter = SQLModelAdapter(model=Article, get_session=get_session)
    disable_delete = True
    dependencies = [Depends(require_auth)]
    create_dependencies = [Depends(require_admin)]
```

This is handy when several collections share common configuration:

```python
class AuthenticatedCRUD(CRUDCollection):
    dependencies = [Depends(require_auth)]

class ArticleCRUD(AuthenticatedCRUD):
    orm_adapter = SQLModelAdapter(model=Article, get_session=get_session)

class CommentCRUD(AuthenticatedCRUD):
    orm_adapter = SQLModelAdapter(model=Comment, get_session=get_session)
```

## Custom ID path

By default, `CRUDCollection` builds a path like `/{article_id}` from the model name.
Override `apply_pk_aliases` to change this:

```python
class ArticleCRUD(CRUDCollection):
    def apply_pk_aliases(self, pk_schema):
        # use /{id} instead of /{article_id}
        return pk_schema
```
