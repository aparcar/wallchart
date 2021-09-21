import os
import tempfile

import pytest
from flask import current_app

import wallchart
from wallchart import db
from wallchart.db import create_tables
from wallchart.util import parse_csv


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
    load_test_data()
    yield app
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def app_with_data(app):
    return app


@pytest.fixture
def client(app):
    with app.test_client() as client:
        with app.app_context():
            yield client


def login(client, email, password):
    return client.post(
        "/login/", data=dict(email=email, password=password), follow_redirects=True
    )


def load_test_data():
    with open("tests/test_roster.csv", "rb") as roster_file:
        parse_csv(roster_file)
    db.Worker.update(
        email="test@test.com",
        password="$2b$12$bKGBVGgi7AzUXIuljVHE8OxPptMM9TxYKTw7qdNQiBDIAZ.jjXxyu",
    ).where(db.Worker.id == 1).execute()
    db.close()


def admin_login(client):
    username = "admin"
    password = current_app.config["ADMIN_PASSWORD"]

    login(client, username, password)


def logout(client):
    return client.get("/logout/", follow_redirects=True)
