"""Forum models — Tortoise ORM implementation.

Same schema as the SQLModel version; used by the Tortoise adapter tests.
"""
from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=255)

    class Meta:
        table = "user"


class Category(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    created_at = fields.DatetimeField(auto_now_add=True, null=True)
    updated_at = fields.DatetimeField(auto_now=True, null=True)

    class Meta:
        table = "category"


class Thread(Model):
    id = fields.IntField(pk=True)
    category: fields.ForeignKeyRelation[Category] = fields.ForeignKeyField(
        "models.Category", related_name="threads",
    )
    title = fields.CharField(max_length=255)

    class Meta:
        table = "thread"


class Post(Model):
    id = fields.IntField(pk=True)
    thread: fields.ForeignKeyRelation[Thread] = fields.ForeignKeyField(
        "models.Thread", related_name="posts",
    )
    author: fields.ForeignKeyNullableRelation[User] = fields.ForeignKeyField(
        "models.User",
        related_name="posts",
        null=True,
    )
    slug = fields.CharField(max_length=255)
    created_at = fields.DatetimeField(auto_now_add=True, null=True)
    updated_at = fields.DatetimeField(auto_now=True, null=True)

    class Meta:
        table = "post"


class Tag(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)

    class Meta:
        table = "tag"


class PostTranslation(Model):
    # Tortoise does not support composite PKs; language serves as the PK.
    # Uniqueness per post is enforced via unique_together on (post_id, language).
    language = fields.CharField(max_length=10, primary_key=True)
    post: fields.ForeignKeyRelation[Post] = fields.ForeignKeyField(
        "models.Post", related_name="translations",
    )
    body = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True, null=True)
    updated_at = fields.DatetimeField(auto_now=True, null=True)

    class Meta:
        table = "posttranslation"
        unique_together = (("post_id", "language"),)
