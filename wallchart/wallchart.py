import configparser
import csv
import io
import logging
from datetime import date
from functools import wraps
from pathlib import Path

import bcrypt
from flask import (
    Flask,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from peewee import (
    JOIN,
    BooleanField,
    Case,
    CharField,
    DateField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
    fn,
)
from slugify import slugify
from wallchart.database import *

config = configparser.ConfigParser()
config.read("config.ini")

logger = logging.getLogger("peewee")
logger.addHandler(logging.StreamHandler())
logger.setLevel(config["logging"]["level"])


DATABASE = config["database"]["path"]
SECRET_KEY = config["flask"]["secret"]

assert SECRET_KEY != "changeme", "Change flask secret in config.ini"

assert config["admin"]["password"] != "changeme", "Change admin password in config.ini"


app = Flask(__name__)
app.config.from_object(__name__)

database = SqliteDatabase(DATABASE)


def bcryptify(password: str):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode("utf-8")


def get_current_user():
    if session.get("logged_in"):
        return Worker.get(Worker.id == session["user_id"])


def is_admin():
    return session.get("admin", False)


def login_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return inner


@app.before_request
def before_request():
    g.db = database
    g.db.connect()


@app.after_request
def after_request(response):
    g.db.close()
    return response


def parse_csv(csv_file_b):
    with io.TextIOWrapper(csv_file_b, encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=";")

        for row in reader:
            department, _ = Department.get_or_create(
                name=row["Job Sect Desc"].title(),
                slug=slugify(row["Job Sect Desc"]),
            )

            worker, created = Worker.get_or_create(
                name=row["Name"],
                contract=row["Job Code"],
                department_id=department.id,
                # default organizing_dept to department ID, can be changed later on
                organizing_dept_id=department.id,
                unit=row["Unit"],
            )
            worker.update(updated=date.today())


if __name__ == "__main__":
    if not Path(DATABASE).exists():
        create_tables()

    app.run()
