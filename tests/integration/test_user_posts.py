"""User /me CRUD with stub PK dependency + FK name mismatch.

Demonstrates the lasertagbase pattern: PKFieldsDependency is replaced
with a stub so /users/me/posts resolves the current user without a path
param, while the FK mapping author_id → User.id (column names differ)
is handled automatically by _fk_values_from_parent.
"""


async def _setup(user_client) -> tuple[dict, dict]:
    """Create user (id=1 via auto-increment) and a thread for thread_id."""
    user = (
        await user_client.post("/users", json={"username": "alice"})
    ).json()
    cat = (
        await user_client.post("/categories", json={"name": "Python"})
    ).json()
    thread = (
        await user_client.post(
            f"/categories/{cat['id']}/threads",
            json={"title": "Async"},
        )
    ).json()
    return user, thread


async def test_me_posts_author_id_auto_filled(user_client) -> None:
    """Post.author_id (FK) != User.id (PK) — filled from stub, not body."""
    user, thread = await _setup(user_client)

    r = await user_client.post(
        "/users/me/posts",
        json={"slug": "asyncio", "thread_id": thread["id"]},
    )
    assert r.status_code == 200
    post = r.json()
    assert post["author_id"] == user["id"]


async def test_me_posts_scoped_to_stub_user(user_client) -> None:
    """GET /users/me/posts returns only posts belonging to stub user."""
    user, thread = await _setup(user_client)

    await user_client.post(
        "/users/me/posts",
        json={"slug": "asyncio", "thread_id": thread["id"]},
    )
    await user_client.post(
        "/users/me/posts",
        json={"slug": "trio", "thread_id": thread["id"]},
    )

    r = await user_client.get("/users/me/posts")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    assert all(p["author_id"] == user["id"] for p in data["data"])


async def test_me_posts_parent_not_found_when_user_missing(
    user_client,
) -> None:
    """POST /users/me/posts returns 404 when stub user doesn't exist in DB."""
    cat = (
        await user_client.post("/categories", json={"name": "Python"})
    ).json()
    thread = (
        await user_client.post(
            f"/categories/{cat['id']}/threads",
            json={"title": "Async"},
        )
    ).json()

    r = await user_client.post(
        "/users/me/posts",
        json={"slug": "asyncio", "thread_id": thread["id"]},
    )
    assert r.status_code == 404


def test_me_routes_use_literal_segment_not_pk_param(user_posts_app) -> None:
    """get_id_path -> "/me" pins the segment; no {user_id} placeholder.

    Guards the routing itself, not just the runtime: a stub could make
    a real /users/{user_id}/posts pass every request test above by
    catching "me" as a throwaway param, so assert the path shape here.
    """
    paths = {getattr(r, "path", "") for r in user_posts_app.routes}

    assert "/users/me" in paths
    assert "/users/me/posts" in paths
    assert not any("{user_id}" in p for p in paths)
