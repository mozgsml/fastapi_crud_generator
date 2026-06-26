"""Forum models — SQLModel implementation.

Demonstrates:
- Simple int PK:     Category, Thread, Post, Tag
- 1:many (3 levels): Category → Thread → Post
- Composite PK:      PostTranslation(post_id, language)
- Composite FK:      PostTranslationTag → PostTranslation
- M2M:               PostTranslation ↔ Tag via PostTranslationTag
- Server defaults:   created_at/updated_at on Category and Post
"""
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import ForeignKeyConstraint
from sqlmodel import Column, Field, SQLModel


class Category(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(sa.DateTime, server_default=sa.func.now()),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            sa.DateTime,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


class Thread(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    category_id: int = Field(foreign_key="category.id")
    title: str


class Post(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    thread_id: int = Field(foreign_key="thread.id")
    slug: str
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(sa.DateTime, server_default=sa.func.now()),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            sa.DateTime,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


class Tag(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str


class PostTranslation(SQLModel, table=True):
    """Post body in a specific language. Composite PK: (post_id, language)."""

    post_id: int = Field(primary_key=True, foreign_key="post.id")
    language: str = Field(primary_key=True)
    body: str
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(sa.DateTime, server_default=sa.func.now()),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            sa.DateTime,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


class PostTranslationTag(SQLModel, table=True):
    """M2M: PostTranslation ↔ Tag. Composite FK → PostTranslation."""

    __table_args__ = (
        ForeignKeyConstraint(
            ["post_id", "language"],
            ["posttranslation.post_id", "posttranslation.language"],
        ),
    )

    post_id: int = Field(primary_key=True)
    language: str = Field(primary_key=True)
    tag_id: int = Field(primary_key=True, foreign_key="tag.id")
