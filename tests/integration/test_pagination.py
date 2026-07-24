"""Pagination via ?page=&per_page=, with a total count in the envelope."""


async def _seed(client, n: int) -> None:
    for i in range(n):
        await client.post("/categories", json={"name": f"cat-{i:02d}"})


async def test_envelope_reports_page_and_total_count(client):
    await _seed(client, 5)

    r = await client.get("/categories", params={"page": 1, "per_page": 2})

    assert r.status_code == 200
    data = r.json()
    assert set(data) == {"page", "per_page", "count", "data"}
    assert data["page"] == 1
    assert data["per_page"] == 2
    assert data["count"] == 5  # total across all pages, not this page
    assert len(data["data"]) == 2


async def test_pages_slice_the_result_set(client):
    await _seed(client, 5)

    first = (
        await client.get("/categories", params={"page": 1, "per_page": 2})
    ).json()
    last = (
        await client.get("/categories", params={"page": 3, "per_page": 2})
    ).json()

    assert len(first["data"]) == 2
    assert len(last["data"]) == 1  # 5 items, 2 per page -> last page holds 1
    first_ids = {c["id"] for c in first["data"]}
    last_ids = {c["id"] for c in last["data"]}
    assert first_ids.isdisjoint(last_ids)
