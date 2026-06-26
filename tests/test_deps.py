"""Tests for all ReplaceSignatureDependency subclasses."""
import uuid
from inspect import Parameter
from typing import Annotated

import pytest
from fastapi.params import Depends
from pydantic import BaseModel, Field

from fastapi_crud_generator.deps import (
    ConstantDependency,
    CreateSchemaDependency,
    FilterSchemaDependency,
    PaginatorDependency,
    ParentPKFieldsDependency,
    PKFieldsDependency,
    ReplaceWithAnnotationDependency,
)
from fastapi_crud_generator.paginator import PaginatorBase
from fastapi_crud_generator.schemas import ParentRef


def make_param(name: str = "param") -> Parameter:
    # Minimal Parameter stub for passing into get_new_params() in tests.
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

    def test_pack_to_originals_returns_value_under_original_name(self):
        dep = CreateSchemaDependency(SampleSchema)
        sentinel = object()
        result = dep.pack_to_originals("x", x=sentinel)
        assert result is sentinel


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
        pk = dep.pack_to_originals("pk_field_values", id=val)
        assert isinstance(pk, SamplePK)
        assert pk.id == val

    def test_pack_to_originals_maps_alias_to_field(self):
        dep = PKFieldsDependency(SamplePKAliased)
        val = uuid.uuid4()
        pk = dep.pack_to_originals("pk_field_values", user_id=val)
        assert isinstance(pk, SamplePKAliased)
        assert pk.id == val

    def test_parent_pk_fields_dependency_uses_alias(self):
        base = PKFieldsDependency(SamplePKAliased)
        dep = ParentPKFieldsDependency(base_dep=base, model=object)
        params = dep.get_new_params(make_param("parent_pk"))
        assert params[0].name == "user_id"


# ---------------------------------------------------------------------------
# ConstantDependency
# ---------------------------------------------------------------------------

class TestConstantDependency:

    def test_removes_param_from_signature(self):
        dep = ConstantDependency([])
        assert dep.get_new_params(make_param("p")) == []

    def test_returns_fixed_value(self):
        dep = ConstantDependency([])
        result = dep.pack_to_originals("p", other="x")
        assert result == []

    def test_returns_none(self):
        dep = ConstantDependency(None)
        result = dep.pack_to_originals("p")
        assert result is None

    def test_returns_arbitrary_object(self):
        sentinel = object()
        dep = ConstantDependency(sentinel)
        result = dep.pack_to_originals("p")
        assert result is sentinel


# ---------------------------------------------------------------------------
# ParentPKFieldsDependency
# ---------------------------------------------------------------------------

class FakeModel:
    """Dummy ORM model used as ParentRef.model in tests."""


class FakeChildModel:
    """Dummy child ORM model."""


class FakeGrandChildModel:
    """Dummy grandchild ORM model (third level)."""


class OrgPK(BaseModel):
    id: uuid.UUID = Field(validation_alias="org_id")


class UserPK(BaseModel):
    id: uuid.UUID = Field(validation_alias="user_id")


class GamePK(BaseModel):
    id: uuid.UUID = Field(validation_alias="game_id")


class CompositePK(BaseModel):
    user_id: uuid.UUID
    club_id: uuid.UUID


class TestParentPKFieldsDependency:

    def test_single_level_get_new_params(self):
        base = PKFieldsDependency(UserPK)
        dep = ParentPKFieldsDependency(base_dep=base, model=FakeModel)
        params = dep.get_new_params(make_param("parent_refs"))
        assert len(params) == 1
        assert params[0].name == "user_id"

    def test_single_level_pack_to_originals(self):
        base = PKFieldsDependency(UserPK)
        dep = ParentPKFieldsDependency(base_dep=base, model=FakeModel)
        val = uuid.uuid4()
        refs = dep.pack_to_originals("parent_refs", user_id=val)
        assert len(refs) == 1
        assert isinstance(refs[0], ParentRef)
        assert refs[0].model is FakeModel
        assert refs[0].pk_values.id == val  # type: ignore[attr-defined]

    def test_two_level_get_new_params(self):
        org_base = PKFieldsDependency(OrgPK)
        user_base = PKFieldsDependency(UserPK)
        grandparent = ParentPKFieldsDependency(
            base_dep=org_base, model=FakeModel,
        )
        dep = ParentPKFieldsDependency(
            base_dep=user_base,
            model=FakeChildModel,
            parent_dep=grandparent,
        )
        params = dep.get_new_params(make_param("parent_refs"))
        names = [p.name for p in params]
        assert names == ["org_id", "user_id"]

    def test_two_level_pack_to_originals(self):
        org_base = PKFieldsDependency(OrgPK)
        user_base = PKFieldsDependency(UserPK)
        grandparent = ParentPKFieldsDependency(
            base_dep=org_base, model=FakeModel,
        )
        dep = ParentPKFieldsDependency(
            base_dep=user_base,
            model=FakeChildModel,
            parent_dep=grandparent,
        )
        dep.get_new_params(make_param("parent_refs"))
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        refs = dep.pack_to_originals(
            "parent_refs", org_id=org_id, user_id=user_id,
        )
        assert len(refs) == 2
        assert refs[0].model is FakeChildModel
        assert refs[0].pk_values.id == user_id  # type: ignore[attr-defined]
        assert refs[1].model is FakeModel
        assert refs[1].pk_values.id == org_id  # type: ignore[attr-defined]

    def test_with_constant_dependency_as_parent_dep(self):
        base = PKFieldsDependency(UserPK)
        dep = ParentPKFieldsDependency(
            base_dep=base,
            model=FakeModel,
            parent_dep=ConstantDependency([]),
        )
        val = uuid.uuid4()
        refs = dep.pack_to_originals("parent_refs", user_id=val)
        assert len(refs) == 1
        assert refs[0].model is FakeModel

    def test_annotation_dep_as_base_dep(self):
        """base_dep = ReplaceWithAnnotationDependency (e.g. users/me auth).

        The annotation dep keeps the param name unchanged; FastAPI injects
        the value under original_name, so pack_to_originals wraps it as-is.
        """
        annotation = Annotated[UserPK, Depends(lambda: None)]
        base = ReplaceWithAnnotationDependency(annotation)
        dep = ParentPKFieldsDependency(base_dep=base, model=FakeModel)

        # Simulate FastAPI injecting UserPK under original_name
        val = uuid.uuid4()
        injected_pk = UserPK.model_validate({"user_id": val})
        refs = dep.pack_to_originals("parent_refs", parent_refs=injected_pk)

        assert len(refs) == 1
        assert isinstance(refs[0], ParentRef)
        assert refs[0].model is FakeModel
        assert refs[0].pk_values is injected_pk

    def _three_level_dep(self) -> ParentPKFieldsDependency:
        # /orgs/{org_id}/users/{user_id}/games/{game_id}/...
        grandparent = ParentPKFieldsDependency(
            base_dep=PKFieldsDependency(OrgPK), model=FakeModel,
        )
        parent = ParentPKFieldsDependency(
            base_dep=PKFieldsDependency(UserPK),
            model=FakeChildModel,
            parent_dep=grandparent,
        )
        return ParentPKFieldsDependency(
            base_dep=PKFieldsDependency(GamePK),
            model=FakeGrandChildModel,
            parent_dep=parent,
        )

    def test_three_level_get_new_params(self):
        dep = self._three_level_dep()
        params = dep.get_new_params(make_param("parent_refs"))
        names = [p.name for p in params]
        assert names == ["org_id", "user_id", "game_id"]

    def test_three_level_pack_to_originals(self):
        dep = self._three_level_dep()
        dep.get_new_params(make_param("parent_refs"))
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        game_id = uuid.uuid4()
        refs = dep.pack_to_originals(
            "parent_refs", org_id=org_id, user_id=user_id, game_id=game_id,
        )
        assert len(refs) == 3
        assert [r.model for r in refs] == [
            FakeGrandChildModel, FakeChildModel, FakeModel,
        ]
        assert [r.pk_values.id for r in refs] == [game_id, user_id, org_id]

    def test_constant_dependency_as_parent_dep_with_prebuilt_refs(self):
        # Break the chain with a fixed, non-empty ancestor list.
        preset = [
            ParentRef(model=FakeModel, pk_values=OrgPK(org_id=uuid.uuid4())),
        ]
        dep = ParentPKFieldsDependency(
            base_dep=PKFieldsDependency(UserPK),
            model=FakeChildModel,
            parent_dep=ConstantDependency(preset),
        )
        user_id = uuid.uuid4()
        refs = dep.pack_to_originals("parent_refs", user_id=user_id)
        assert len(refs) == 2
        assert refs[0].model is FakeChildModel
        assert refs[0].pk_values.id == user_id  # type: ignore[attr-defined]
        assert refs[1] is preset[0]

    def test_composite_parent_pk(self):
        dep = ParentPKFieldsDependency(
            base_dep=PKFieldsDependency(CompositePK), model=FakeModel,
        )
        params = dep.get_new_params(make_param("parent_refs"))
        assert {p.name for p in params} == {"user_id", "club_id"}

        user_id = uuid.uuid4()
        club_id = uuid.uuid4()
        refs = dep.pack_to_originals(
            "parent_refs", user_id=user_id, club_id=club_id,
        )
        assert len(refs) == 1
        assert refs[0].pk_values.user_id == user_id  # type: ignore[attr-defined]
        assert refs[0].pk_values.club_id == club_id  # type: ignore[attr-defined]


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
