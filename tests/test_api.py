from tests.conftest import admin_login, load_test_data

# /api/workers


def test_api_workers_nologin(client):
    rv = client.get("/api/workers")
    assert rv.status_code == 302


def test_api_workers_login_empty(client):
    admin_login(client)
    rv = client.get("/api/workers")
    assert rv.status_code == 200
    assert rv.json == []


def test_api_workers_login_data(client):
    load_test_data()
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
    rv = client.get("/api/worker/1")
    assert rv.status_code == 404


def test_api_worker_login_data(client):
    load_test_data()
    admin_login(client)
    rv = client.get("/api/worker/1")
    assert rv.status_code == 200
    assert rv.json["active"] == True
    assert rv.json["id"] == 1


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


def test_api_departments_login_empty(client):
    admin_login(client)
    rv = client.get("/api/departments")
    assert rv.status_code == 200
    assert rv.json == []


# /api/units


def test_api_units_nologin(client):
    rv = client.get("/api/units")
    assert rv.status_code == 302


def test_api_units_login_empty(client):
    admin_login(client)
    rv = client.get("/api/units")
    assert rv.status_code == 200
    assert rv.json == []
