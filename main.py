import csv
import io
import logging
from datetime import date
from functools import wraps
from hashlib import sha256
from pathlib import Path

from flask import (
    Flask,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from peewee import (
    JOIN,
    BooleanField,
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
    organizing_dept_id = IntegerField()
    active = BooleanField(default=True)
    added = DateField(default=date.today)
    updated = DateField(default=date.today)

    class Meta:
        indexes = ((("name", "unit", "department_id", "contract"), True),)


class Unit(BaseModel):
    name = CharField(unique=True)
    slug = CharField()


class Department(BaseModel):
    name = CharField(unique=True)
    slug = CharField()
    alias = CharField(unique=True, null=True)
    unit = ForeignKeyField(Unit, backref="departments", null=True)


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
            [Worker, Unit, Department, User, StructureTest, Participation]
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


@app.route("/")
def homepage():
    if session.get("logged_in"):
        if session.get("department_id") == 0:
            return redirect(url_for("admin"))
        else:
            return redirect(url_for("department"))
    else:
        return redirect(url_for("login"))


@app.route("/admin")
def admin():
    return render_template("admin.html")


@app.route("/structure_test", methods=["GET", "POST"])
@app.route("/structure_test/<int:structure_test_id>", methods=["GET", "POST"])
def structure_test(structure_test_id=None):
    if request.method == "POST":
        if structure_test_id:
            if request.form.get("delete"):
                StructureTest.delete().where(
                    StructureTest.id == structure_test_id
                ).execute()
                Participation.delete().where(
                    Participation.structure_test == structure_test_id,
                ).execute()
                flash("Deleted Structure Test")
                return redirect(url_for("structure_tests"))

            StructureTest.update(
                name=request.form["name"],
                description=request.form["description"],
                active=bool(request.form.get("active")),
            ).where(StructureTest.id == structure_test_id).execute()
            flash("Structure test updated")
        else:
            structure_test, created = StructureTest.get_or_create(
                name=request.form["name"], description=request.form["description"]
            )
            if created:
                flash(f"Added Structure Test '{ structure_test.name }'")
            else:
                flash("Structure test already exists")
            return redirect(
                url_for("structure_test", structure_test_id=structure_test.id)
            )

    if structure_test_id:
        structure_test = StructureTest.get(StructureTest.id == structure_test_id)
    else:
        structure_test = None

    return render_template("structure_test.html", structure_test=structure_test)


@app.route("/find_worker")
def find_worker():
    return render_template("find_worker.html")


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


@app.route("/units/", methods=["GET", "POST"])
@login_required
def units():
    if request.method == "POST":
        Unit.create(
            name=request.form["name"],
            slug=slugify(request.form["name"]),
        )
        flash("Unit created")

    units = Unit.select().group_by(Unit.name)
    return render_template("units.html", units=units)


@app.route("/departments/")
@login_required
def departments():
    departments = Department.select().order_by(Department.name)
    department_count = len(departments)
    return render_template(
        "departments.html",
        departments=departments,
        department_count=department_count,
    )


@app.route("/department/")
@app.route("/department/<path:department_slug>", methods=["GET", "POST"])
@login_required
def department(department_slug=None):
    if department_slug:
        department = Department.get(Department.slug == department_slug)
    else:
        department = Department.get(Department.id == session["department_id"])

    if request.method == "POST":
        # only admins can switch department alias
        if session.get("department_id") == 0:
            Department.update(alias=request.form["alias"]).where(
                Department.slug == department_slug
            ).execute()
        flash("Department updated")

    workers = (
        Worker.select(
            Worker,
            fn.group_concat(Participation.structure_test)
            .python_value(
                lambda idlist: [int(i) for i in (idlist.split(",") if idlist else [])]
            )
            .alias("participated"),
        )
        .join(Participation, JOIN.LEFT_OUTER, on=(Worker.id == Participation.worker))
        .where(
            (Worker.organizing_dept_id == department.id)
            | (Worker.department_id == department.id)
        )
        .group_by(Worker.id)
        .order_by(Worker.name, Participation.structure_test)
    )

    last_updated = Worker.select(fn.MAX(Worker.updated)).scalar()
    units = Unit.select().order_by(Unit.name)

    structure_tests = StructureTest.select().order_by(StructureTest.added)

    return render_template(
        "department.html",
        workers=workers,
        worker_count=len(workers),
        department=department,
        structure_tests=structure_tests,
        last_updated=last_updated,
        units=units,
    )


@app.route("/api/workers")
@login_required
def api_workers():
    return jsonify(
        list(
            Worker.select(
                Worker,
                Department.slug.alias("department_slug"),
                Department.name.alias("department_name"),
            )
            .join(Department, on=(Worker.organizing_dept_id == Department.id))
            .dicts()
        )
    )


@app.route("/api/participation")
@login_required
def api_participation():
    return jsonify(list(Participation.select().dicts()))


@app.route("/api/departments")
@login_required
def api_departments():
    return jsonify(list(Department.select().dicts()))


@app.route("/structure_tests", methods=["GET", "POST"])
@login_required
def structure_tests():
    structure_tests = (
        StructureTest.select(
            StructureTest, fn.count(Participation.id).alias("participation")
        )
        .join(
            Participation,
            JOIN.LEFT_OUTER,
            on=(StructureTest.id == Participation.structure_test),
        )
        .group_by(StructureTest.id)
        .order_by(StructureTest.added)
    )
    worker_count = (
        Worker.select(fn.count(Worker.id)).where(Worker.active == True).scalar()
    )
    return render_template(
        "structure_tests.html",
        structure_tests=structure_tests,
        worker_count=worker_count,
    )


@app.route("/worker/<int:worker_id>", methods=["GET", "POST"])
@login_required
def worker(worker_id):
    if request.method == "POST":

        update = {
            Worker.preferred_name: request.form["preferred_name"],
            Worker.pronouns: request.form["pronouns"],
            Worker.email: request.form["email"] or None,
            Worker.phone: request.form["phone"] or None,
            Worker.notes: request.form["notes"],
            Worker.active: bool(request.form.get("active")),
        }

        # only admins can switch worker departments
        if session.get("department_id") == 0:
            update[Worker.organizing_dept_id] = request.form["organizing_dept"]

        Worker.update(update).where(Worker.id == worker_id).execute()
        flash("Worker data updated")

    worker = Worker.get(Worker.id == worker_id)
    return render_template("worker.html", worker=worker, Department=Department)


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


@app.route("/set-department-unit/<int:unit_id>/<int:department_id>")
def set_department_unit(unit_id, department_id):
    if session.get("department_id") != 0:
        return "", 400

    Department.update(unit=unit_id).where(Department.id == department_id).execute()
    return ""


@app.route("/participation/<int:worker_id>/<int:structure_test_id>/<int:status>")
def participation(worker_id, structure_test_id, status):
    worker = Worker.get(Worker.id == worker_id)
    if (
        session.get("department_id") == worker.organizing_dept_id
        or session.get("department_id") == 0
    ):
        if status == 1:
            Participation.create(worker=worker_id, structure_test=structure_test_id)
        else:
            Participation.delete().where(
                Participation.worker == worker_id,
                Participation.structure_test == structure_test_id,
            ).execute()
        return ""
    else:
        return "", 400


@app.route("/logout/")
def logout():
    session.clear()
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
                # default organizing_dept to department ID, can be changed later on
                organizing_dept_id=department.id,
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

    app.run()
