"""Forum models — pure SQLAlchemy (DeclarativeBase) implementation.

Same schema as the SQLModel version; used by the SQLAlchemy adapter tests.
"""
import datetime

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(sa.String(255))


class Category(Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(255))
    created_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime, server_default=sa.func.now(), nullable=True,
    )
    updated_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=True,
    )
    threads: Mapped[list["Thread"]] = relationship(
        back_populates="category",
    )


class Thread(Base):
    __tablename__ = "thread"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("category.id"),
    )
    title: Mapped[str] = mapped_column(sa.String(255))
    posts: Mapped[list["Post"]] = relationship(back_populates="thread")
    category: Mapped[Category | None] = relationship(
        back_populates="threads",
    )


class Post(Base):
    __tablename__ = "post"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("thread.id"),
    )
    author_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("user.id"), nullable=True,
    )
    slug: Mapped[str] = mapped_column(sa.String(255))
    thread: Mapped[Thread | None] = relationship(back_populates="posts")
    created_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime, server_default=sa.func.now(), nullable=True,
    )
    updated_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=True,
    )


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(255))


class PostTranslation(Base):
    __tablename__ = "posttranslation"

    post_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("post.id"), primary_key=True,
    )
    language: Mapped[str] = mapped_column(sa.String(10), primary_key=True)
    body: Mapped[str] = mapped_column(sa.Text)
    created_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime, server_default=sa.func.now(), nullable=True,
    )
    updated_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=True,
    )
