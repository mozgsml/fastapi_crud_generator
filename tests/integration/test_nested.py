"""Nested route tests — Category → Thread → Post (3 levels)."""


async def test_threads_scoped_to_category(client):
    cat_a = (await client.post("/categories", json={"name": "Python"})).json()
    cat_b = (await client.post("/categories", json={"name": "Go"})).json()

    await client.post(
        f"/categories/{cat_a['id']}/threads",
        json={"category_id": cat_a["id"], "title": "Async"},
    )
    await client.post(
        f"/categories/{cat_a['id']}/threads",
        json={"category_id": cat_a["id"], "title": "Typing"},
    )
    await client.post(
        f"/categories/{cat_b['id']}/threads",
        json={"category_id": cat_b["id"], "title": "Goroutines"},
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
        json={"category_id": cat["id"], "title": "Async"},
    )).json()
    thread_b = (await client.post(
        f"/categories/{cat['id']}/threads",
        json={"category_id": cat["id"], "title": "Typing"},
    )).json()

    base = f"/categories/{cat['id']}/threads"
    await client.post(
        f"{base}/{thread_a['id']}/posts",
        json={"thread_id": thread_a["id"], "slug": "asyncio"},
    )
    await client.post(
        f"{base}/{thread_a['id']}/posts",
        json={"thread_id": thread_a["id"], "slug": "trio"},
    )
    await client.post(
        f"{base}/{thread_b['id']}/posts",
        json={"thread_id": thread_b["id"], "slug": "pep-484"},
    )

    r = await client.get(f"{base}/{thread_a['id']}/posts")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    assert {p["slug"] for p in data["data"]} == {"asyncio", "trio"}


async def test_get_single_post_scoped(client):
    cat = (await client.post("/categories", json={"name": "Python"})).json()
    thread = (await client.post(
        f"/categories/{cat['id']}/threads",
        json={"category_id": cat["id"], "title": "Async"},
    )).json()

    base = f"/categories/{cat['id']}/threads/{thread['id']}/posts"
    post = (await client.post(
        base, json={"thread_id": thread["id"], "slug": "asyncio"},
    )).json()

    r = await client.get(f"{base}/{post['id']}")
    assert r.status_code == 200
    assert r.json()["slug"] == "asyncio"
