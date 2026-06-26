"""Nested route tests — Category → Thread → Post (3 levels)."""


async def _setup_two_categories(client):
    """Return (cat_a, cat_b, thread_a_in_cat_a)."""
    cat_a = (await client.post("/categories", json={"name": "Python"})).json()
    cat_b = (await client.post("/categories", json={"name": "Go"})).json()
    thread = (await client.post(
        f"/categories/{cat_a['id']}/threads",
        json={"title": "Async"},
    )).json()
    return cat_a, cat_b, thread


async def test_threads_scoped_to_category(client):
    cat_a = (await client.post("/categories", json={"name": "Python"})).json()
    cat_b = (await client.post("/categories", json={"name": "Go"})).json()

    await client.post(
        f"/categories/{cat_a['id']}/threads",
        json={"title": "Async"},
    )
    await client.post(
        f"/categories/{cat_a['id']}/threads",
        json={"title": "Typing"},
    )
    await client.post(
        f"/categories/{cat_b['id']}/threads",
        json={"title": "Goroutines"},
    )

    r = await client.get(f"/categories/{cat_a['id']}/threads")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    assert {t["title"] for t in data["data"]} == {"Async", "Typing"}


async def test_posts_scoped_to_thread(client):
    cat = (await client.post("/categories", json={"name": "Python"})).json()

    thread_a = (await client.post(
        f"/categories/{cat['id']}/threads",
        json={"title": "Async"},
    )).json()
    thread_b = (await client.post(
        f"/categories/{cat['id']}/threads",
        json={"title": "Typing"},
    )).json()

    base = f"/categories/{cat['id']}/threads"
    await client.post(f"{base}/{thread_a['id']}/posts", json={"slug": "asyncio"})
    await client.post(f"{base}/{thread_a['id']}/posts", json={"slug": "trio"})
    await client.post(f"{base}/{thread_b['id']}/posts", json={"slug": "pep-484"})

    r = await client.get(f"{base}/{thread_a['id']}/posts")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    assert {p["slug"] for p in data["data"]} == {"asyncio", "trio"}


async def test_get_single_post_scoped(client):
    cat = (await client.post("/categories", json={"name": "Python"})).json()
    thread = (await client.post(
        f"/categories/{cat['id']}/threads",
        json={"title": "Async"},
    )).json()

    base = f"/categories/{cat['id']}/threads/{thread['id']}/posts"
    post = (await client.post(base, json={"slug": "asyncio"})).json()

    r = await client.get(f"{base}/{post['id']}")
    assert r.status_code == 200
    assert r.json()["slug"] == "asyncio"


async def test_get_one_wrong_parent_returns_404(client):
    cat_a, cat_b, thread = await _setup_two_categories(client)

    r = await client.get(f"/categories/{cat_b['id']}/threads/{thread['id']}")
    assert r.status_code == 404


async def test_update_wrong_parent_returns_404(client):
    cat_a, cat_b, thread = await _setup_two_categories(client)

    r = await client.patch(
        f"/categories/{cat_b['id']}/threads/{thread['id']}",
        json={"title": "Hacked"},
    )
    assert r.status_code == 404


async def test_delete_wrong_parent_returns_404(client):
    cat_a, cat_b, thread = await _setup_two_categories(client)

    r = await client.delete(
        f"/categories/{cat_b['id']}/threads/{thread['id']}",
    )
    assert r.status_code == 404


async def test_fk_field_not_required_in_nested_create(client):
    """category_id must not be required in body — value comes from URL."""
    cat = (await client.post("/categories", json={"name": "Python"})).json()

    r = await client.post(
        f"/categories/{cat['id']}/threads",
        json={"title": "Async"},
    )
    assert r.status_code == 200
    assert r.json()["category_id"] == cat["id"]
