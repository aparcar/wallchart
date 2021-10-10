from tests.conftest import admin_login

# /api/workers


def test_api_workers_nologin(client):
    rv = client.get("/api/workers")
    assert rv.status_code == 302


def test_api_workers_login_data(client):
    admin_login(client)
    rv = client.get("/api/workers")
    assert rv.status_code == 200
    assert len(rv.json) == 10


# /api/worker


def test_api_worker_nologin(client):
    rv = client.get("/api/worker/1")
    assert rv.status_code == 302


def test_api_worker_login_not_found(client):
    admin_login(client)
    rv = client.get("/api/worker/100")
    assert rv.status_code == 404


def test_api_worker_login_data(client):
    admin_login(client)
    rv = client.get("/api/worker/1")
    assert rv.status_code == 200
    assert rv.json["active"] == True
    assert rv.json["id"] == 1
    assert rv.json["email"] == "test@test.com"
    assert (
        rv.json["password"]
        == "$2b$12$bKGBVGgi7AzUXIuljVHE8OxPptMM9TxYKTw7qdNQiBDIAZ.jjXxyu"
    )


# /api/participation


def test_api_participation_nologin(client):
    rv = client.get("/api/participation")
    assert rv.status_code == 302


def test_api_participation_login(client):
    admin_login(client)
    rv = client.get("/api/participation")
    assert rv.status_code == 200
    assert rv.json == []


# /api/departments


def test_api_departments_nologin(client):
    rv = client.get("/api/departments")
    assert rv.status_code == 302


def test_api_departments(client):
    admin_login(client)
    rv = client.get("/api/departments")
    assert rv.status_code == 200
    assert len(rv.json) == 10


# /api/units


def test_api_units_nologin(client):
    rv = client.get("/api/units")
    assert rv.status_code == 302


def test_api_units(client):
    admin_login(client)
    rv = client.get("/api/units")
    assert rv.status_code == 200
    assert len(rv.json) == 0
