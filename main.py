from peewee import SqliteDatabase
from peewee import Model
from peewee import CharField
import io
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
from peewee import fn

import csv

import logging

logger = logging.getLogger("peewee")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)


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
    preferred_name = CharField(null=True)
    pronouns = CharField(null=True)
    email = CharField(unique=True, null=True)
    phone = IntegerField(unique=True, null=True)
    notes = TextField(null=True)
    contract = CharField()
    unit = CharField()
    department_id = IntegerField()
    active = BooleanField(default=True)
    added = DateField(default=date.today)
    updated = DateField(default=date.today)

    class Meta:
        indexes = ((("name", "unit", "department_id", "contract"), True),)


class College(BaseModel):
    name = CharField(unique=True)
    slug = CharField()


class Department(BaseModel):
    name = CharField(unique=True)
    slug = CharField()
    college = ForeignKeyField(College, backref="departments", null=True)


class User(BaseModel):
    email = CharField(unique=True)
    password = CharField()
    department = ForeignKeyField(Department, backref="chair", null=True)


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
        database.create_tables(
            [Worker, College, Department, User, StructureTest, Participation]
        )


def auth_user(user):
    session["logged_in"] = True
    session["user_id"] = user.id
    session["email"] = user.email
    session["department_id"] = user.department.id
    flash(f"You are logged in as {user.email}")


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
        if session.get("department_id") == 0:
            return redirect(url_for("admin"))
        else:
            return redirect(url_for("workers"))
    else:
        return redirect(url_for("login"))


@app.route("/admin")
def admin():
    return render_template("admin.html")


@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "POST" and request.form["email"]:
        try:
            pw_hash = sha256(request.form["password"].encode("utf-8")).hexdigest()
            user = User.get(
                (User.email == request.form["email"]) & (User.password == pw_hash)
            )
        except User.DoesNotExist:
            flash("The password entered is incorrect")
        else:
            auth_user(user)
            return redirect(url_for("homepage"))
    return render_template("login.html")


@app.route("/colleges/", methods=["GET", "POST"])
@login_required
def colleges():
    if request.method == "POST":
        College.create(
            name=request.form["name"],
            slug=slugify(request.form["name"]),
        )
        flash("College created")

    colleges = College.select().group_by(College.name)
    return render_template("colleges.html", colleges=colleges)


@app.route("/departments/")
@login_required
def departments():
    departments = Department.select().order_by(Department.name)
    department_count = len(departments)
    return object_list(
        "departments.html",
        departments,
        "department_list",
        department_count=department_count,
    )


@app.route("/workers/<path:department_slug>")
@app.route("/workers/")
@login_required
def workers(department_slug=None):
    if department_slug and session.get("department_id") == 0:
        department = Department.get(Department.slug == department_slug)
    else:
        department = Department.get(Department.id == session.get("department_id"))

    workers = (
        Worker.select(Worker, Participation)
        .join(Participation, JOIN.LEFT_OUTER, on=(Worker.id == Participation.worker))
        .where(Worker.department_id == department.id)
        .order_by(Worker.name)
    )

    last_updated = Worker.select(fn.MAX(Worker.updated)).scalar()
    colleges = College.select().order_by(College.name)

    structure_tests = StructureTest.select().order_by(StructureTest.added)

    return object_list(
        "workers.html",
        workers,
        "worker_list",
        worker_count=len(workers),
        department=department,
        structure_test_list=structure_tests,
        last_updated=last_updated,
        colleges=colleges,
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
                Worker.preferred_name: request.form["preferred_name"],
                Worker.pronouns: request.form["pronouns"],
                Worker.email: request.form["email"],
                Worker.phone: request.form["phone"],
                Worker.notes: request.form["notes"],
                Worker.active: request.form["active"],
            }
        ).where(Worker.id == worker_id).execute()
        flash("Worker data updated")

    worker = Worker.get(Worker.id == worker_id)
    return render_template("workers_edit.html", worker=worker)


@app.route("/users/", methods=["GET", "POST"])
@login_required
def users():
    if request.method == "POST":
        if request.form.get("id"):
            update = {
                User.email: request.form["email"],
                User.department: request.form["department"],
            }
            if request.form.get("password"):
                update[User.password] = sha256(
                    request.form["password"].encode("utf-8")
                ).hexdigest()

            User.update(update).where(User.id == request.form["id"]).execute()
            flash("User updated")
        else:
            User.create(
                email=request.form["email"],
                password=sha256(request.form["password"].encode("utf-8")).hexdigest(),
                department=request.form["department"],
            )
            flash("User created")

    users = User.select()
    departments = Department.select().order_by(Department.name)
    return render_template("users.html", users=users, departments=departments)


@app.route("/set-department-college/<int:college_id>/<int:department_id>")
def set_department_college(college_id, department_id):
    if session.get("department_id") != 0:
        return "", 400

    Department.update(college=college_id).where(
        Department.id == department_id
    ).execute()
    return ""


@app.route("/participation/<int:worker_id>/<int:structure_test_id>/<int:status>")
def participation(worker_id, structure_test_id, status):
    worker = Worker.get(Worker.id == worker_id)
    if (
        session.get("department_id") == worker.department_id
        or session.get("department_id") == 0
    ):
        if status == 1:
            Participation.create(worker=worker_id, structure_test=structure_test_id)
        else:
            Participation.delete().where(
                Participation.worker == worker_id,
                Participation.structure_test == structure_test_id,
            )
        return ""
    else:
        return "", 400


@app.route("/logout/")
def logout():
    session.pop("logged_in", None)
    flash("You were logged out")
    return redirect(url_for("homepage"))


@app.route("/upload_record", methods=["GET", "POST"])
@login_required
def upload_record():
    new_workers = []
    if request.method == "POST":
        if "record" not in request.files:
            flash("Missing file")
            return redirect(request.url)
        record = request.files["record"]

        if record.filename == "":
            flash("No selected file")
            return redirect(request.url)

        if not record.filename.lower().endswith(".csv"):
            flash("Wrong filetye, convert to CSV please")
            return redirect(request.url)

        if record:
            parse_csv(record)
            new_workers = (
                Worker.select(Worker, Department)
                .join(Department, on=(Worker.department_id == Department.id))
                .where(Worker.updated == date.today())
            )
            flash(f"Found {len(new_workers)} new workers")

    return render_template("upload_record.html", new_workers=new_workers)


def parse_csv(csv_file_b):
    with io.TextIOWrapper(csv_file_b, encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=";")

        for row in reader:
            department, _ = Department.get_or_create(
                name=row["Dept ID Desc"].title(),
                slug=slugify(row["Dept ID Desc"]),
            )

            worker, created = Worker.get_or_create(
                name=row["Name"],
                contract=row["Job Code"],
                department_id=department.id,
                unit=row["Unit"],
            )
            worker.update(updated=date.today())


if __name__ == "__main__":
    if not Path(DATABASE).exists():
        create_tables()
        Department.get_or_create(
            id=0,
            name="Admin",
            slug="admin",
        )
        User.get_or_create(
            email="admin@admin.com",
            password=sha256("admin".encode("utf-8")).hexdigest(),
            department=0,
        )

    Participation.get_or_create(worker=625, structure_test=1)
    Participation.get_or_create(worker=625, structure_test=2)

    app.run()
