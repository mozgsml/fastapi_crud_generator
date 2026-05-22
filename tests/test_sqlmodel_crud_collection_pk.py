"""Tests for CRUDCollection pk_fields auto-generation via SQLModelAdapter."""
import uuid

from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from fastapi_crud_generator import CRUDCollection
from fastapi_crud_generator.orm.sqlmodel import SQLModelAdapter


async def _fake_session():
    yield None


def make_adapter(model) -> SQLModelAdapter:
    return SQLModelAdapter(get_session=_fake_session, model=model)


class ItemUUID(SQLModel, table=True):
    __tablename__ = "test_collection_pk_item_uuid"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str


class ItemCompositePK(SQLModel, table=True):
    __tablename__ = "test_collection_pk_item_composite"

    user_id: int = Field(primary_key=True)
    club_id: int = Field(primary_key=True)
    title: str


# ---------------------------------------------------------------------------
# pk_fields auto-generation
# ---------------------------------------------------------------------------

class TestPKFieldsAutoGeneration:

    def test_pk_fields_derived_from_adapter_when_not_set(self):
        crud = CRUDCollection(orm_adapter=make_adapter(ItemUUID))
        assert set(crud.pk_fields.model_fields) == {"id"}

    def test_explicit_pk_fields_on_class_overrides_adapter(self):
        class CustomPK(BaseModel):
            slug: str

        class CustomCRUD(CRUDCollection):
            orm_adapter = make_adapter(ItemUUID)
            pk_fields = CustomPK  # noqa: RUF012

        crud = CustomCRUD()
        assert set(crud.pk_fields.model_fields) == {"slug"}

    def test_explicit_pk_fields_in_init_overrides_adapter(self):
        class CustomPK(BaseModel):
            slug: str

        crud = CRUDCollection(
            orm_adapter=make_adapter(ItemUUID),
            pk_fields=CustomPK,
        )
        assert set(crud.pk_fields.model_fields) == {"slug"}

    def test_composite_pk_all_fields_present(self):
        crud = CRUDCollection(orm_adapter=make_adapter(ItemCompositePK))
        assert set(crud.pk_fields.model_fields) == {"user_id", "club_id"}


# ---------------------------------------------------------------------------
# id_path
# ---------------------------------------------------------------------------

class TestIdPath:

    def test_single_pk_path(self):
        crud = CRUDCollection(orm_adapter=make_adapter(ItemUUID))
        assert crud.id_path == "/{itemuuid_id}"

    def test_composite_pk_path_contains_both_fields(self):
        crud = CRUDCollection(orm_adapter=make_adapter(ItemCompositePK))
        assert "{user_id}" in crud.id_path
        assert "{club_id}" in crud.id_path

    def test_manual_pk_fields_without_alias_uses_field_name(self):
        class ManualPK(BaseModel):
            id: uuid.UUID

        crud = CRUDCollection(
            orm_adapter=make_adapter(ItemUUID),
            pk_fields=ManualPK,
        )
        assert crud.id_path == "/{id}"
