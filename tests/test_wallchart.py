import os
import io
import tempfile

import pytest

import wallchart
from wallchart.db import create_tables

from datetime import date


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
        "/login/", data=dict(email=email, password=password), follow_redirects=True
    )


def logout(client):
    return client.get("/logout/", follow_redirects=True)


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


def test_upload_record(app, client):
    """xxx"""
    rv = login(client, "admin", app.config["ADMIN_PASSWORD"])
    assert rv.status_code == 200

    data = {}
    with open("tests/test_roster.csv", 'rb') as roster_file:
        data["record"] = (roster_file, "roster.csv")
        rv = client.post("/upload_record", data=data, follow_redirects=True,
        content_type='multipart/form-data'
        )
        print(rv.data)
        assert rv.status_code == 200

    rv = client.get("/worker/1")
    assert b"Space" in rv.data
        


#def test_add_worker(app, client):
#    """xXx"""
#    rv = login(client, "admin", app.config["ADMIN_PASSWORD"])
#    assert rv.status_code == 200
#
#    data = dict(
#        name="Test,Worker",
#        contract="manual",
#        department_id=0,
#        organizing_dept=0,
#        updated=date.today(),
#        unit=0,
#        preferred_name="Worka",
#        pronouns="he/him",
#        email="test@worker.com",
#        notes="These are notes",
#        active=True,
#    )
#
#    rv = client.post("/worker/", data=data, follow_redirects=True)
#    print(rv.data)
#    assert rv.status_code == 200
