"""Reverse-direction nested routes: Post → Thread → Category.

Demonstrates bidirectional add_nested_collection: Post.thread_id → thread
means Thread is the data-parent, but when registered under post_crud, the
library should auto-detect the FK direction and produce:

    GET /posts/{post_id}/threads
    GET /posts/{post_id}/threads/{thread_id}/categories
"""


async def _setup(root_client) -> tuple[dict, dict, dict]:
    """Return (category, thread, post)."""
    cat = (
        await root_client.post("/categories", json={"name": "Python"})
    ).json()
    thread = (
        await root_client.post(
            "/threads",
            json={"title": "Async", "category_id": cat["id"]},
        )
    ).json()
    post = (
        await root_client.post(
            "/posts",
            json={"slug": "asyncio", "thread_id": thread["id"]},
        )
    ).json()
    return cat, thread, post


async def test_get_thread_for_post(root_client) -> None:
    """GET /posts/{post_id}/threads returns the thread containing that post."""
    _cat, thread, post = await _setup(root_client)

    r = await root_client.get(f"/posts/{post['id']}/threads")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["data"][0]["id"] == thread["id"]


async def test_get_category_for_post_via_thread(root_client) -> None:
    """GET /posts/{post_id}/threads/{thread_id}/categories returns category."""
    cat, thread, post = await _setup(root_client)

    r = await root_client.get(
        f"/posts/{post['id']}/threads/{thread['id']}/categories",
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["data"][0]["id"] == cat["id"]


async def test_wrong_thread_id_returns_empty(root_client) -> None:
    """GET /posts/{post_id}/threads/{wrong_id}/categories is empty or 404."""
    cat, thread, post = await _setup(root_client)

    r = await root_client.get(
        f"/posts/{post['id']}/threads/999/categories",
    )
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        assert r.json()["count"] == 0
