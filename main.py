from peewee import SqliteDatabase
from peewee import Model
from peewee import CharField
from peewee import BooleanField
from peewee import TextField
from peewee import ForeignKeyField
from peewee import IntegerField
from peewee import DeferredForeignKey
from peewee import DateField
from peewee import CompositeKey
from peewee import AutoField
from peewee import JOIN

from flask import Flask
from flask import g
from flask import session
from flask import flash
from flask import redirect
from flask import url_for
from flask import request
from flask import render_template

from functools import wraps
from hashlib import sha256
from pathlib import Path
from slugify import slugify
from datetime import date


import csv

import logging

# logger = logging.getLogger("peewee")
# logger.addHandler(logging.StreamHandler())
# logger.setLevel(logging.DEBUG)


DATABASE = "wallcharts.db"
DEBUG = True
SECRET_KEY = "seeCho2deisi6ahwach4ohw4Daeghee3"

app = Flask(__name__)
app.config.from_object(__name__)

database = SqliteDatabase(DATABASE)


class BaseModel(Model):
    class Meta:
        database = database


class Worker(BaseModel):
    name = CharField()
    email = CharField(unique=True, null=True)
    phone = IntegerField(unique=True, null=True)
    notes = TextField(null=True)
    contract = CharField()
    unit = CharField()
    department_id = IntegerField()
    active = BooleanField(default=True)
    added = DateField(default=date.today)
    updated = DateField()

    class Meta:
        indexes = ((("name", "unit", "department_id", "contract"), True),)


class Department(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField()
    chair = ForeignKeyField(Worker, field="id", backref="chair", null=True)
    slug = CharField()


class User(BaseModel):
    username = CharField(unique=True)
    password = CharField()
    email = CharField(unique=True)


class StructureTest(BaseModel):
    name = CharField(unique=True)
    description = TextField()
    active = BooleanField(default=True)
    added = DateField(default=date.today)


class Participation(BaseModel):
    worker = ForeignKeyField(Worker, field="id")
    structure_test = ForeignKeyField(StructureTest)


def create_tables():
    with database:
        database.create_tables([Worker, Department, User, StructureTest, Participation])


def auth_user(user):
    session["logged_in"] = True
    session["user_id"] = user.id
    session["username"] = user.username
    flash(f"You are logged in as {user.username}")


def get_current_user():
    if session.get("logged_in"):
        return User.get(User.id == session["user_id"])


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


def object_list(template_name, qr, var_name="object_list", **kwargs):
    entries_per_page = 30
    kwargs.update(
        page=int(request.args.get("page", 1)), pages=qr.count() / entries_per_page + 1
    )
    kwargs[var_name] = qr.paginate(kwargs["page"], entries_per_page)
    return render_template(template_name, **kwargs)


@app.route("/")
def homepage():
    if session.get("logged_in"):
        return redirect(url_for("login"))
    else:
        return redirect(url_for("login"))


@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "POST" and request.form["username"]:
        try:
            pw_hash = sha256(request.form["password"].encode("utf-8")).hexdigest()
            user = User.get(
                (User.username == request.form["username"]) & (User.password == pw_hash)
            )
        except User.DoesNotExist:
            flash("The password entered is incorrect")
        else:
            auth_user(user)
            return redirect(url_for("homepage"))
    return render_template("login.html")


@app.route("/departments/")
@login_required
def departments():
    departments = Department.select().order_by(Department.name.desc())
    return object_list("departments.html", departments, "department_list")


@app.route("/workers/<path:department_slug>")
@login_required
def workers(department_slug):
    department = Department.get(Department.slug == department_slug)

    workers = (
        Worker.select()
        .join(Participation, JOIN.LEFT_OUTER, on=(Worker.id == Participation.worker))
        .where(Worker.department_id == department.id or "*")
        .order_by(Worker.name)
    )
    structure_tests = StructureTest.select().order_by(StructureTest.added)
    print(structure_tests)

    return object_list(
        "workers.html",
        workers,
        "worker_list",
        worker_count=len(workers),
        department=department,
        structure_test_list=structure_tests,
    )


@app.route("/structure_tests", methods=["GET", "POST"])
@login_required
def structure_tests():
    if request.method == "POST":
        structure_test, created = StructureTest.get_or_create(
            name=request.form["name"], description=request.form["description"]
        )
        if created:
            flash("Structure Test added")
        else:
            flash("Structure test already exists")

    structure_tests = StructureTest.select().order_by(StructureTest.added)
    return object_list("structure_tests.html", structure_tests, "structure_tests_list")


@app.route("/workers/edit/<int:worker_id>", methods=["GET", "POST"])
@login_required
def workers_edit(worker_id):
    if request.method == "POST":
        Worker.update(
            {
                Worker.email: request.form["email"],
                Worker.phone: request.form["phone"],
                Worker.notes: request.form["notes"],
            }
        ).where(Worker.id == worker_id).execute()
        flash("Worker data updated")

    worker = Worker.get(Worker.id == worker_id)
    return render_template("workers_edit.html", worker=worker)


@app.route("/logout/")
def logout():
    session.pop("logged_in", None)
    flash("You were logged out")
    return redirect(url_for("homepage"))


def parse_csv():
    with open("roster.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")

        for row in reader:
            print(row)
            department, created = Department.get_or_create(
                id=row["Dept ID"],
                name=row["Dept ID Desc"].title(),
                slug=slugify(row["Dept ID Desc"]),
            )
            if created:
                print(slugify(row["Dept ID Desc"]))
            # flash(f"New Department added: {department.name}")
            Worker.get_or_create(
                name=row["Name"],
                contract=row["Job Code"],
                department_id=row["Dept ID"],
                unit=row["Unit"],
                updated=date.today(),
            )


if __name__ == "__main__":
    if not Path(DATABASE).exists():
        create_tables()
        parse_csv()
    User.get_or_create(
        username="admin",
        password=sha256("admin".encode("utf-8")).hexdigest(),
        email="admin@admin.com",
    )

    Participation.get_or_create(worker=1281, structure_test=1)

    app.run()
