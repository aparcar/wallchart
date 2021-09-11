import os
import tempfile

import pytest

import wallchart
from wallchart.db import create_tables


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    app = wallchart.create_app(
        {
            "ADMIN_PASSWORD": "admin",
            "DATABASE": f"sqlite:///{db_path}",
            "SECRET_KEY": "test",
            "TESTING": True,
        }
    )
    create_tables()
    yield app
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    with app.test_client() as client:
        with app.app_context():
            yield client


def test_empty_db(client):
    rv = client.get("/")
    assert rv.status_code == 302


def login(client, email, password):
    return client.post(
        "/login", data=dict(email=email, password=password), follow_redirects=True
    )


def logout(client):
    return client.get("/logout", follow_redirects=True)


def test_login_logout(app, client):
    """Make sure login and logout works."""

    username = "admin"
    password = app.config["ADMIN_PASSWORD"]

    rv = login(client, username, password)
    assert rv.status_code == 200

    rv = logout(client)
    assert rv.status_code == 200

    rv = login(client, f"{username}x", password)
    assert rv.status_code == 403

    rv = login(client, username, f"{password}x")
    assert rv.status_code == 403
