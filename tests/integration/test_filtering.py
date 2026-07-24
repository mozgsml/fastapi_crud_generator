"""Filtering via query params — every scalar field becomes a filter."""


async def _seed(client) -> None:
    for name in ("apple", "banana", "cherry"):
        await client.post("/categories", json={"name": name})


async def test_filter_by_field_returns_only_matches(client):
    await _seed(client)

    r = await client.get("/categories", params={"name": "apple"})

    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert [c["name"] for c in data["data"]] == ["apple"]


async def test_filter_without_match_returns_empty(client):
    await _seed(client)

    r = await client.get("/categories", params={"name": "durian"})

    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 0
    assert data["data"] == []


async def test_no_filter_returns_everything(client):
    await _seed(client)

    r = await client.get("/categories")

    assert r.status_code == 200
    assert r.json()["count"] == 3
