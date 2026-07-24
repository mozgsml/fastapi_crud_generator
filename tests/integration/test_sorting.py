"""Sorting via ?sort=field:direction."""


async def _seed(client) -> None:
    for name in ("banana", "apple", "cherry"):
        await client.post("/categories", json={"name": name})


async def test_sort_ascending(client):
    await _seed(client)

    r = await client.get("/categories", params={"sort": "name:asc"})

    assert r.status_code == 200
    names = [c["name"] for c in r.json()["data"]]
    assert names == ["apple", "banana", "cherry"]


async def test_sort_descending(client):
    await _seed(client)

    r = await client.get("/categories", params={"sort": "name:desc"})

    assert r.status_code == 200
    names = [c["name"] for c in r.json()["data"]]
    assert names == ["cherry", "banana", "apple"]
