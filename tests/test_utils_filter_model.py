from enum import Enum
from pydantic import BaseModel
from typing import Optional, List, Dict
from fastapi_crud_generator.utils import create_filter_model


class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class SampleModel(BaseModel):
    name: str # Should remain in filter (string)
    age: int # Should remain (integer)
    price: float # Should remain (float)
    is_active: bool # Should remain (boolean)
    status: Status # Should remain (enum)
    status_or_none: Status | None = None # Should remain (enum)
    tags: List[str] # Should be filtered out (list)
    metadata: Dict[str, str] # Should be filtered out (dict)
    optional_field: Optional[str] # Should remain (optional string)
    complex_field: Optional[List[int]] # Should be filtered out (optional list)

    new_optional_field: str | None = None


def test_model_keeps_primitive_and_enum_fields():
    """Verify that only primitive types and enums remain in the filter"""
    filtered_model = create_filter_model(SampleModel)

    # Check expected fields are present
    assert "name" in filtered_model.model_fields # String
    assert "age" in filtered_model.model_fields # Integer
    assert "price" in filtered_model.model_fields # Float
    assert "is_active" in filtered_model.model_fields # Boolean
    assert "status" in filtered_model.model_fields # Enum
    assert "status_or_none" in filtered_model.model_fields # Enum
    assert "optional_field" in filtered_model.model_fields # Optional string
    assert "new_optional_field" in filtered_model.model_fields # Optional string

    # Verify complex types are filtered out
    assert "tags" not in filtered_model.model_fields # List
    assert "metadata" not in filtered_model.model_fields # Dict
    assert "complex_field" not in filtered_model.model_fields # Optional list


def test_filtered_fields_are_optional():
    """Verify all fields in filter become optional"""
    filtered_model = create_filter_model(SampleModel)

    for field in filtered_model.model_fields.values():
        assert not field.is_required()  # Field should not be required


def test_filtered_model_usage():
    """Test practical usage of the filtered model"""
    filtered_model = create_filter_model(SampleModel)

    # Create instance with partial data
    instance = filtered_model(
        name="Test",
        age=None,
        status=None,
        optional_field="value"
    )

    # Verify field values
    assert instance.name == "Test"
    assert instance.age is None
    assert instance.status is None
    assert instance.optional_field == "value"
    assert instance.status_or_none is None
    assert instance.price is None
