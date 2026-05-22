"""Tests for all ReplaceSignatureDependency subclasses."""
import uuid
from inspect import Parameter
from typing import Annotated

import pytest
from fastapi.params import Depends
from pydantic import BaseModel, Field

from fastapi_crud_generator.deps import (
    CreateSchemaDependency,
    FilterSchemaDependency,
    PaginatorDependency,
    ParentPKFieldsDependency,
    PKFieldsDependency,
    ReplaceWithAnnotationDependency,
)
from fastapi_crud_generator.paginator import PaginatorBase


def make_param(name: str = "param") -> Parameter:
    return Parameter(name, Parameter.POSITIONAL_OR_KEYWORD)


class SampleSchema(BaseModel):
    name: str
    age: int


class SamplePK(BaseModel):
    id: uuid.UUID


class SamplePKAliased(BaseModel):
    id: uuid.UUID = Field(validation_alias="user_id")


# ---------------------------------------------------------------------------
# ReplaceSingleSignatureDependency
# ---------------------------------------------------------------------------

class TestReplaceSingleSignatureDependency:

    def test_replaces_annotation_keeps_name(self):
        dep = CreateSchemaDependency(SampleSchema)
        params = dep.get_new_params(make_param("create_data"))
        assert len(params) == 1
        assert params[0].name == "create_data"
        assert params[0].annotation is SampleSchema

    def test_pack_to_originals_returns_kwargs_unchanged(self):
        dep = CreateSchemaDependency(SampleSchema)
        result = dep.pack_to_originals("x", foo="bar")
        assert result == {"foo": "bar"}


# ---------------------------------------------------------------------------
# ReplaceWithAnnotationDependency / PaginatorDependency
# ---------------------------------------------------------------------------

class TestReplaceWithAnnotationDependency:

    def test_replaces_with_arbitrary_annotation(self):
        annotation = Annotated[str, "some_meta"]
        dep = ReplaceWithAnnotationDependency(annotation)
        params = dep.get_new_params(make_param("p"))
        assert len(params) == 1
        assert params[0].annotation is annotation

    def test_paginator_dependency_wraps_in_depends(self):
        dep = PaginatorDependency(PaginatorBase)
        params = dep.get_new_params(make_param("paginator"))
        annotation = params[0].annotation
        assert hasattr(annotation, "__metadata__")
        assert any(isinstance(m, Depends) for m in annotation.__metadata__)


# ---------------------------------------------------------------------------
# ReplaceSubDependency
# ---------------------------------------------------------------------------

class TestReplaceSubDependency:

    def test_returns_single_annotated_param(self):
        dep = FilterSchemaDependency(SampleSchema)
        params = dep.get_new_params(make_param("filter_data"))
        assert len(params) == 1
        assert params[0].name == "filter_data"

    def test_annotation_is_annotated_with_depends(self):
        dep = FilterSchemaDependency(SampleSchema)
        params = dep.get_new_params(make_param("filter_data"))
        annotation = params[0].annotation
        assert hasattr(annotation, "__metadata__")
        assert any(isinstance(m, Depends) for m in annotation.__metadata__)


# ---------------------------------------------------------------------------
# ReplaceWithParamsListDependency
# ---------------------------------------------------------------------------

class TestReplaceWithParamsListDependency:

    def test_field_name_used_when_no_alias(self):
        dep = PKFieldsDependency(SamplePK)
        params = dep.get_new_params(make_param("pk"))
        assert len(params) == 1
        assert params[0].name == "id"
        assert params[0].annotation is uuid.UUID

    def test_validation_alias_used_as_param_name(self):
        dep = PKFieldsDependency(SamplePKAliased)
        params = dep.get_new_params(make_param("pk"))
        assert len(params) == 1
        assert params[0].name == "user_id"
        assert params[0].annotation is uuid.UUID

    def test_multiple_fields_expand_to_multiple_params(self):
        class CompositePK(BaseModel):
            user_id: int
            club_id: int

        dep = PKFieldsDependency(CompositePK)
        params = dep.get_new_params(make_param("pk"))
        assert {p.name for p in params} == {"user_id", "club_id"}

    def test_pack_to_originals_without_alias(self):
        dep = PKFieldsDependency(SamplePK)
        val = uuid.uuid4()
        result = dep.pack_to_originals("pk_field_values", id=val)
        pk = result["pk_field_values"]
        assert isinstance(pk, SamplePK)
        assert pk.id == val

    def test_pack_to_originals_maps_alias_to_field(self):
        dep = PKFieldsDependency(SamplePKAliased)
        val = uuid.uuid4()
        result = dep.pack_to_originals("pk_field_values", user_id=val)
        pk = result["pk_field_values"]
        assert isinstance(pk, SamplePKAliased)
        assert pk.id == val

    def test_pack_to_originals_preserves_other_kwargs(self):
        dep = PKFieldsDependency(SamplePKAliased)
        val = uuid.uuid4()
        result = dep.pack_to_originals(
            "pk_field_values", user_id=val, other="foo",
        )
        assert result["other"] == "foo"
        assert "user_id" not in result

    def test_parent_pk_fields_dependency_uses_alias(self):
        dep = ParentPKFieldsDependency(SamplePKAliased)
        params = dep.get_new_params(make_param("parent_pk"))
        assert params[0].name == "user_id"


# ---------------------------------------------------------------------------
# ReplaceSignatureDependency.__init__ validation
# ---------------------------------------------------------------------------

class TestReplaceSignatureDependencyInit:

    def test_rejects_non_class(self):
        with pytest.raises(AssertionError):
            CreateSchemaDependency(SampleSchema(name="x", age=1))

    def test_rejects_non_basemodel_class(self):
        with pytest.raises(AssertionError):
            CreateSchemaDependency(str)
