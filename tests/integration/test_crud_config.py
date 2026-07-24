"""Field control via crud_config and via explicit params — every ORM.

These run across all configured backends, so they prove the crud_config
mechanism is honoured by every adapter, not just SQLModel.
"""
from fastapi_crud_generator.config import CRUDConfigDict


def test_crud_config_on_model_controls_generated_fields(
    make_adapter, forum_models, monkeypatch,
):
    monkeypatch.setattr(
        forum_models.Post,
        "crud_config",
        CRUDConfigDict(create_fields={"slug"}, update_fields={"slug"}),
        raising=False,
    )
    adapter = make_adapter(forum_models.Post)

    create = adapter.generate_create_schema(None, None)
    update = adapter.generate_update_schema(None, None)

    assert set(create.model_fields) == {"slug"}
    assert set(update.model_fields) == {"slug"}


def test_explicit_fields_override_crud_config(
    make_adapter, forum_models, monkeypatch,
):
    monkeypatch.setattr(
        forum_models.Post,
        "crud_config",
        CRUDConfigDict(create_fields={"slug"}),
        raising=False,
    )
    adapter = make_adapter(forum_models.Post)

    # the explicit arg is what a collection passes as create_fields=...
    create = adapter.generate_create_schema({"slug", "author_id"}, None)

    assert set(create.model_fields) == {"slug", "author_id"}
