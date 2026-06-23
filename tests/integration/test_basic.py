"""Basic CRUD route tests — Category (simple int PK)."""


async def test_create_and_get(client):
    r = await client.post("/categories", json={"name": "Python"})
    assert r.status_code == 200
    created = r.json()
    assert created["name"] == "Python"
    cat_id = created["id"]

    r = await client.get(f"/categories/{cat_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "Python"


async def test_list(client):
    for name in ("Python", "Go", "Rust"):
        await client.post("/categories", json={"name": name})

    r = await client.get("/categories")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 3
    assert {c["name"] for c in data["data"]} == {"Python", "Go", "Rust"}


async def test_update(client):
    r = await client.post("/categories", json={"name": "OldName"})
    cat_id = r.json()["id"]

    r = await client.patch(f"/categories/{cat_id}", json={"name": "NewName"})
    assert r.status_code == 200

    r = await client.get(f"/categories/{cat_id}")
    assert r.json()["name"] == "NewName"


async def test_delete(client):
    r = await client.post("/categories", json={"name": "ToDelete"})
    cat_id = r.json()["id"]

    r = await client.delete(f"/categories/{cat_id}")
    assert r.status_code == 200

    r = await client.get(f"/categories/{cat_id}")
    assert r.status_code == 404


async def test_get_not_found(client):
    r = await client.get("/categories/999")
    assert r.status_code == 404
