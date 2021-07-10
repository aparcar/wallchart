from peewee import SqliteDatabase
from peewee import Model
from peewee import CharField
from peewee import BooleanField
from peewee import TextField
from peewee import ForeignKeyField
from peewee import IntegerField
from peewee import DeferredForeignKey
from peewee import DateField

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

import csv


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
    contract = IntegerField()
    department = DeferredForeignKey("Department", backref="department")
    active = BooleanField(default=True)


class Department(BaseModel):
    name = CharField(unique=True)
    chair = ForeignKeyField(Worker, backref="chair", null=True)


class User(BaseModel):
    username = CharField(unique=True)
    password = CharField()
    email = CharField(unique=True)


class StructureTests(BaseModel):
    name = CharField(unique=True)
    description = TextField()
    active = BooleanField()
    date = DateField()


class Participation(BaseModel):
    worker = ForeignKeyField(Worker)
    structure_test = ForeignKeyField(StructureTests)


def create_tables():
    with database:
        database.create_tables(
            [Worker, Department, User, StructureTests, Participation]
        )


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
def departments():
    departments = Department.select().order_by(Department.name.desc())
    return object_list("departments.html", departments, "department_list")


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
            department = Department.get_or_create(name=row["Dept ID Desc"].title())
            worker = Worker.update(
                name=row["Name"],
                contract=int(row["Job Code"][2:3]),
                department=department,
            )


if __name__ == "__main__":
    create_tables()
    parse_csv()
    # User.get_or_create(
    #    username="admin",
    #    password=sha256("admin".encode("utf-8")).hexdigest(),
    #    email="admin@admin.com",
    # )

    # for department in Path("departments").read_text().splitlines():
    #    print(department)
    #    Department.get_or_create(name=department.title())

    app.run()
