from wallchart import util
from tests.conftest import login
import bcrypt


def test_bcryptify():
    assert bcrypt.checkpw(b"test", util.bcryptify("test").encode())


def test_is_admin(app, client):
    rv = login(client, "admin", app.config["ADMIN_PASSWORD"])
    assert rv.status_code == 200

    assert util.is_admin()


def test_get_current_user(app, client):
    rv = login(client, "test@test.com", "test")
    assert rv.status_code == 200

    assert util.get_current_user().id == 1
