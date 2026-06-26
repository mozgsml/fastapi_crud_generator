"""Composite PK/FK tests — Post → PostTranslation(post_id, language)."""


async def _create_post(client, slug: str) -> dict:
    cat = (await client.post("/categories", json={"name": "Python"})).json()
    thread = (await client.post(
        f"/categories/{cat['id']}/threads",
        json={"category_id": cat["id"], "title": "Async"},
    )).json()
    return (await client.post(
        f"/categories/{cat['id']}/threads/{thread['id']}/posts",
        json={"thread_id": thread["id"], "slug": slug},
    )).json()


async def test_create_and_get_translation(client):
    post = await _create_post(client, "asyncio")
    post_id = post["id"]

    r = await client.post(
        f"/posts/{post_id}/translations",
        json={"language": "en", "body": "Hello"},
    )
    assert r.status_code == 200
    assert r.json()["language"] == "en"

    r = await client.get(f"/posts/{post_id}/translations/en")
    assert r.status_code == 200
    assert r.json()["body"] == "Hello"


async def test_translations_scoped_to_post(client):
    post_a = await _create_post(client, "asyncio")
    post_b = await _create_post(client, "trio")

    await client.post(
        f"/posts/{post_a['id']}/translations",
        json={"language": "en", "body": "Hello"},
    )
    await client.post(
        f"/posts/{post_a['id']}/translations",
        json={"language": "ru", "body": "Привет"},
    )
    await client.post(
        f"/posts/{post_b['id']}/translations",
        json={"language": "en", "body": "Hi"},
    )

    r = await client.get(f"/posts/{post_a['id']}/translations")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    assert {t["language"] for t in data["data"]} == {"en", "ru"}


async def test_update_translation(client):
    post = await _create_post(client, "asyncio")
    post_id = post["id"]

    await client.post(
        f"/posts/{post_id}/translations",
        json={"post_id": post_id, "language": "en", "body": "Old"},
    )

    r = await client.patch(
        f"/posts/{post_id}/translations/en",
        json={"body": "Updated"},
    )
    assert r.status_code == 200

    r = await client.get(f"/posts/{post_id}/translations/en")
    assert r.json()["body"] == "Updated"
