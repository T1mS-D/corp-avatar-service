def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_auth_required(client):
    r = client.get("/api/v1/styles", headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_styles(client):
    ids = {s["id"] for s in client.get("/api/v1/styles").json()}
    assert {"corporate", "brand", "cartoon"} <= ids


def test_create_and_get(client, portrait_b64):
    r = client.post("/api/v1/avatars", json={"image_base64": portrait_b64, "style": "corporate",
                                             "employee_ref": "11111111-2222-3333-4444-555555555555"})
    assert r.status_code == 202
    job = r.json()
    assert job["status"] == "queued"
    got = client.get(f"/api/v1/avatars/{job['id']}").json()
    assert got["employee_ref"] == "11111111-2222-3333-4444-555555555555"
    lst = client.get("/api/v1/avatars", params={"employee_ref": "11111111-2222-3333-4444-555555555555"}).json()
    assert len(lst) == 1
    # результата ещё нет
    assert client.get(f"/api/v1/avatars/{job['id']}/image").status_code == 409
    assert client.delete(f"/api/v1/avatars/{job['id']}").status_code == 204
    assert client.get(f"/api/v1/avatars/{job['id']}").status_code == 404


def test_upload_multipart(client, portrait_bytes):
    r = client.post("/api/v1/avatars/upload", files={"file": ("a.jpg", portrait_bytes, "image/jpeg")},
                    data={"style": "brand"})
    assert r.status_code == 202 and r.json()["style"] == "brand"


def test_bad_inputs(client, portrait_b64):
    assert client.post("/api/v1/avatars", json={"image_base64": portrait_b64, "style": "nope"}).status_code == 400
    import base64
    junk = base64.b64encode(b"not an image").decode()
    assert client.post("/api/v1/avatars", json={"image_base64": junk}).status_code == 400
