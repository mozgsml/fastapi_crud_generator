import pytest
from pydantic import BaseModel, Field, create_model

from fastapi_crud_generator.utils import slice_model, to_optional_fields


class _Source(BaseModel):
    id: int
    name: str = Field(description='Full name')
    age: int = Field(gt=0)
    email: str | None = None


# --- to_optional_fields ---

def test_to_optional_fields_returns_all_fields():
    field_defs = to_optional_fields(_Source)
    assert set(field_defs.keys()) == {'id', 'name', 'age', 'email'}


def test_to_optional_fields_all_become_not_required():
    field_defs = to_optional_fields(_Source)
    for _annotation, field_info in field_defs.values():
        assert not field_info.is_required()


def test_to_optional_fields_preserves_validators():
    M = create_model('M', **to_optional_fields(_Source))
    assert M(age=None).age is None
    with pytest.raises(Exception):
        M(age=-1)


# --- slice_model ---

def test_slice_model_all_fields_when_none():
    M = slice_model('M', _Source)
    assert set(M.model_fields.keys()) == {'id', 'name', 'age', 'email'}


def test_slice_model_keeps_only_given_fields():
    M = slice_model('M', _Source, fields={'id', 'name'})
    assert set(M.model_fields.keys()) == {'id', 'name'}


def test_slice_model_optional_makes_fields_not_required():
    M = slice_model('M', _Source, fields={'id', 'name'}, optional=True)
    assert not M.model_fields['id'].is_required()
    assert not M.model_fields['name'].is_required()


def test_slice_model_preserves_description():
    M = slice_model('M', _Source, fields={'name'})
    assert M.model_fields['name'].description == 'Full name'


def test_slice_model_name():
    M = slice_model('MySchema', _Source)
    assert M.__name__ == 'MySchema'
