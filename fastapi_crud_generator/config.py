from dataclasses import dataclass, field


@dataclass(frozen=True)
class CRUDConfigDict:
    """Configuration for automatic CRUD schema generation.

    Place on a SQLModel table class as ``crud_config`` to control
    how the ORM adapter generates schemas and routes.

    Attributes:
        base_fields: Fields shared across schemas; used as a fallback
            when public_fields, create_fields or update_fields are not set.
        public_fields: Fields exposed in the public (GET) schema.
        create_fields: Fields accepted in the create (POST) schema.
        update_fields: Fields accepted in the update (PATCH) schema.

    """

    base_fields: set[str] = field(default_factory=set)
    public_fields: set[str] = field(default_factory=set)
    create_fields: set[str] = field(default_factory=set)
    update_fields: set[str] = field(default_factory=set)
