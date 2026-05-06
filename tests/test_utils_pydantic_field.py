import uuid
from typing import Annotated, Union

import pytest
from annotated_types import Gt, Lt
from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo

from fastapi_crud_generator.utils import has_none_in_annotation, make_pydantic_field


# --- has_none_in_annotation ---

def test_plain_type():
    assert not has_none_in_annotation(int)

def test_new_style_union_with_none():
    # types.UnionType code path (Python 3.10+)
    assert has_none_in_annotation(int | None)

def test_typing_union_with_none():
    # typing.Union code path
    assert has_none_in_annotation(Union[int, None])

def test_union_without_none():
    assert not has_none_in_annotation(Union[int, str])


# --- make_pydantic_field ---

def test_required_field_stays_required():
    fi = FieldInfo(annotation=str)
    annotation, field_info = make_pydantic_field(fi)
    model = create_model('M', v=(annotation, field_info))
    assert model.model_fields['v'].is_required()


def test_optional_resets_default_factory_to_none():
    fi = FieldInfo(annotation=uuid.UUID, default_factory=uuid.uuid4)
    annotation, field_info = make_pydantic_field(fi, optional=True)
    model = create_model('M', v=(annotation, field_info))
    assert model().v is None


def test_non_optional_preserves_default_factory():
    fi = FieldInfo(annotation=uuid.UUID, default_factory=uuid.uuid4)
    annotation, field_info = make_pydantic_field(fi)
    model = create_model('M', v=(annotation, field_info))
    assert isinstance(model().v, uuid.UUID)


def test_validators_preserved_when_optional():
    fi = Field(gt=0, lt=100)
    fi.annotation = int
    annotation, field_info = make_pydantic_field(fi, optional=True)
    model = create_model('M', v=(annotation, field_info))
    assert model(v=None).v is None
    assert model(v=50).v == 50
    with pytest.raises(Exception):
        model(v=200)


def test_exclude_metadata():
    class OrmMeta:
        pass

    class _Tmp(BaseModel):
        value: Annotated[int, Gt(0), OrmMeta()]

    fi = _Tmp.model_fields['value']
    annotation, field_info = make_pydantic_field(fi, exclude_metadata=(OrmMeta,))
    model = create_model('M', v=(annotation, field_info))
    assert model(v=5).v == 5
    with pytest.raises(Exception):
        model(v=-1)


def test_field_attributes_preserved():
    fi = FieldInfo(annotation=str, description='user email')
    annotation, field_info = make_pydantic_field(fi, optional=True)
    model = create_model('M', v=(annotation, field_info))
    assert model.model_fields['v'].description == 'user email'
