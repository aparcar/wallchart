from tests.conftest import admin_login, login, logout


def test_workers_delete(client):
    admin_login(client)
    rv = client.get("/worker/1/delete", follow_redirects=True)
    assert rv.status_code == 200
    assert b" Deleted worker Yasuoka, Alison M (1)"


def test_workers_delete_not_found(client):
    admin_login(client)
    rv = client.get("/worker/9999999/delete")
    assert rv.status_code == 404
