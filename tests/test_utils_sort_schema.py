from enum import Enum
from typing import Optional, List, Dict

import pytest
from pydantic import BaseModel, ValidationError

from fastapi_crud_generator.utils import create_sort_schema


class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class SampleModel(BaseModel):
    name: str
    age: int
    price: float
    is_active: bool
    status: Status
    status_or_none: Status | None = None
    tags: List[str]
    metadata: Dict[str, str]
    optional_field: Optional[str]
    complex_field: Optional[List[int]]
    new_optional_field: str | None = None


def test_sort_schema_has_sort_field():
    """Verify the generated schema has a single 'sort' field."""
    sort_model = create_sort_schema(SampleModel)
    assert "sort" in sort_model.model_fields


def test_sort_field_is_optional():
    """Verify the 'sort' field is not required."""
    sort_model = create_sort_schema(SampleModel)
    assert not sort_model.model_fields["sort"].is_required()


def test_sort_schema_accepts_valid_values():
    """Verify accepted sort values include plain, :asc and :desc variants."""
    sort_model = create_sort_schema(SampleModel)

    instance = sort_model(sort=["name", "age:asc", "price:desc"])
    assert instance.sort == ["name", "age:asc", "price:desc"]


def test_sort_schema_accepts_none():
    """Verify sort field accepts None."""
    sort_model = create_sort_schema(SampleModel)
    instance = sort_model()
    assert instance.sort is None


def test_sort_schema_excludes_complex_types():
    """Verify complex fields (list, dict) are rejected by validation."""
    sort_model = create_sort_schema(SampleModel)

    with pytest.raises(ValidationError):
        sort_model(sort=["tags"])
    with pytest.raises(ValidationError):
        sort_model(sort=["metadata"])
    with pytest.raises(ValidationError):
        sort_model(sort=["complex_field"])


def test_sort_schema_includes_primitive_fields():
    """Verify primitive and enum fields are accepted in all sort variants."""
    sort_model = create_sort_schema(SampleModel)

    for field in ("name", "age", "price", "is_active", "status"):
        sort_model(sort=[field])
        sort_model(sort=[f"{field}:asc"])
        sort_model(sort=[f"{field}:desc"])
