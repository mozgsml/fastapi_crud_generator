# Customization

## Отключение эндпоинтов

```python
crud = CRUDCollection(
    orm_adapter=adapter,
    disable_delete=True,   # убрать DELETE
    disable_create=True,   # убрать POST
)
```

## Переопределение обработчиков через подкласс

Наследуйтесь от `CRUDCollection` и переопределяйте нужные методы:

```python
from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter

class ArticleCRUD(CRUDCollection):
    orm_adapter = SQLModelAdapter(model=Article, get_session=get_session)

    async def get_one_not_found(self, pk_values, include_data):
        # Кастомный ответ вместо стандартного 404
        raise HTTPException(status_code=404, detail=f"Article not found")

    async def create_one_handler(self, create_data, parent_refs):
        # Доп. логика перед созданием
        create_data.slug = slugify(create_data.title)
        return await super().create_one_handler(create_data, parent_refs)

crud = ArticleCRUD()
app.include_router(crud.get_router(prefix="/articles"))
```

## Атрибуты класса вместо аргументов

Все параметры `CRUDCollection` можно задать как атрибуты класса:

```python
class ArticleCRUD(CRUDCollection):
    orm_adapter = SQLModelAdapter(model=Article, get_session=get_session)
    disable_delete = True
    dependencies = [Depends(require_auth)]
    create_dependencies = [Depends(require_admin)]
```

Это удобно когда несколько `CRUDCollection` разделяют общую конфигурацию:

```python
class AuthenticatedCRUD(CRUDCollection):
    dependencies = [Depends(require_auth)]

class ArticleCRUD(AuthenticatedCRUD):
    orm_adapter = SQLModelAdapter(model=Article, get_session=get_session)

class CommentCRUD(AuthenticatedCRUD):
    orm_adapter = SQLModelAdapter(model=Comment, get_session=get_session)
```

## Кастомный ID в URL

По умолчанию `CRUDCollection` строит путь вида `/{article_id}` из имени модели.
Чтобы изменить это поведение — переопределите `apply_pk_aliases`:

```python
class ArticleCRUD(CRUDCollection):
    def apply_pk_aliases(self, pk_schema):
        # оставить имя поля как есть: /{id} вместо /{article_id}
        return pk_schema
```
