import configparser
import csv
import io
import logging
from datetime import date
from functools import wraps
from pathlib import Path
import yaml

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


class BaseModel(Model):
    class Meta:
        database = database


class Unit(BaseModel):
    name = CharField(unique=True)
    slug = CharField()


class Department(BaseModel):
    name = CharField(unique=True)
    slug = CharField()
    alias = CharField(unique=True, null=True)
    unit = ForeignKeyField(Unit, backref="departments", null=True)


class Worker(BaseModel):
    name = CharField()
    preferred_name = CharField(null=True)
    pronouns = CharField(null=True)
    email = CharField(unique=True, null=True)
    phone = IntegerField(unique=True, null=True)
    notes = TextField(null=True)
    contract = CharField(null=True)
    unit = CharField(null=True)
    department_id = IntegerField(null=True)
    organizing_dept_id = IntegerField(null=True)
    unit_chair_id = ForeignKeyField(Unit, field=Unit.id, backref="chairs", null=True)
    dept_chair_id = ForeignKeyField(
        Department, field=Department.id, backref="chairs", null=True
    )
    active = BooleanField(default=True)
    added = DateField(default=date.today)
    updated = DateField(default=date.today)
    password = CharField(null=True)

    class Meta:
        indexes = ((("name"), True),)


class StructureTest(BaseModel):
    name = CharField(unique=True)
    description = TextField()
    active = BooleanField(default=True)
    added = DateField(default=date.today)


class Participation(BaseModel):
    worker = ForeignKeyField(Worker, field="id")
    structure_test = ForeignKeyField(StructureTest)
    added = DateField(default=date.today)

    class Meta:
        indexes = ((("worker", "structure_test"), True),)


def create_tables():
    with database:
        database.create_tables([Unit, Department, Worker, StructureTest, Participation])


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


@app.route("/")
def homepage():
    if session.get("logged_in"):
        if is_admin():
            return redirect(url_for("admin"))
        else:
            return redirect(url_for("department"))
    else:
        return redirect(url_for("login"))


@app.route("/download_db")
@login_required
def download_db():
    return send_file(
        config["database"]["path"],
        download_name=f"wallchart-backup-{date.today().strftime('%d-%m-%Y')}.db",
    )


@app.route("/admin")
def admin():
    department_count = Department.select(fn.count(Department.id)).scalar()
    worker_count = (
        Worker.select(fn.count(Worker.id)).where(Worker.active == True).scalar()
    )
    return render_template(
        "admin.html", department_count=department_count, worker_count=worker_count
    )


@app.route("/structure_test", methods=["GET", "POST"])
@app.route("/structure_test/<int:structure_test_id>", methods=["GET", "POST"])
def structure_test(structure_test_id=None):
    if request.method == "POST":
        data = dict(
            name=request.form.get("name", "").strip(),
            description=request.form.get("description", "").strip(),
            active=bool(request.form.get("active")),
        )
        if structure_test_id:
            action = request.args.get("action")
            if action == "delete":
                StructureTest.delete().where(
                    StructureTest.id == structure_test_id
                ).execute()
                Participation.delete().where(
                    Participation.structure_test == structure_test_id,
                ).execute()
                flash("Deleted Structure Test")
            else:
                StructureTest.update(data).where(
                    StructureTest.id == structure_test_id
                ).execute()
                flash("Structure test updated")
        else:
            structure_test, created = StructureTest.get_or_create(**data)
            if created:
                flash(f'Added Structure Test "{ structure_test.name }"')
            else:
                flash("Structure test with same name already exists")

        return redirect(url_for("structure_tests"))

    if structure_test_id:
        structure_test = StructureTest.get(StructureTest.id == structure_test_id)
    else:
        structure_test = None

    return render_template("structure_test.html", structure_test=structure_test)


@app.route("/find_worker")
@login_required
def find_worker():
    return render_template("find_worker.html")


@app.route("/login/", methods=["GET", "POST"])
def login():
    status = 200
    if request.method == "POST" and request.form["email"]:
        if (
            request.form["email"] == "admin"
            and request.form["password"] == config["admin"]["password"]
        ):
            session["logged_in"] = True
            session["user_id"] = 0
            session["department_id"] = 0
            session["admin"] = True
            flash(f"You are logged in as administrator.")
            return redirect(url_for("admin"))
        else:
            user = Worker.get_or_none(Worker.email == request.form["email"])

            if user and bcrypt.checkpw(
                request.form.get("password", "").encode(), user.password.encode()
            ):
                session["logged_in"] = True
                session["user_id"] = user.id
                session["email"] = user.email
                session["department_id"] = user.organizing_dept_id
                if user.unit_chair_id:
                    session["admin"] = True
                flash(f"You are logged in as {user.email}")
                return redirect(url_for("department"))
            else:
                # add pseudo operation to avoid timing attacks
                bcrypt.checkpw(
                    request.form["password"].encode(),
                    "$2b$12$L9jjpO8UOMTUiBSw3ptx2OiFf762t9IUfO/5s3HQzH.NpA9bUdFZ.".encode(),
                )

                status = 403
                flash("Wrong user or password")

    return render_template("login.html"), status


@app.route("/units/")
@login_required
def units_view():
    latest_test = (
        StructureTest.select(StructureTest.id, StructureTest.name)
        .order_by(StructureTest.id.desc())
        .get()
    )

    last_updated = Worker.select(fn.MAX(Worker.updated)).scalar()
    units = (
        Unit.select(
            Unit,
            fn.count(Worker.id).alias("worker_count"),
            fn.sum(Case(Participation.structure_test, ((1, 1),), 0)).alias("members"),
            fn.sum(Case(Participation.structure_test, ((latest_test.id, 1),), 0)).alias(
                "latest"
            ),
        )
        .join(Department, JOIN.LEFT_OUTER, on=(Department.unit == Unit.id))
        .join(Worker, JOIN.LEFT_OUTER, on=(Department.id == Worker.organizing_dept_id))
        .join(Participation, JOIN.LEFT_OUTER, on=(Worker.id == Participation.worker))
        .join(
            StructureTest,
            JOIN.LEFT_OUTER,
            on=(Participation.structure_test == StructureTest.id),
        )
        .where(Worker.updated == last_updated)
        .group_by(Unit.id)
    )
    return render_template("units.html", units=units, latest_test_name=latest_test.name)


@app.route("/manage-units/", methods=["GET", "POST"])
@login_required
def units():
    if request.method == "POST":
        action = request.args.get("action")
        if action == "create":
            Unit.create(
                name=request.form["name"],
                slug=slugify(request.form["name"]),
            )
            flash(f"Unit \"{ request.form['name'] }\" created")
            return redirect(url_for("admin"))
        elif action == "delete":
            unit_id = request.args.get("unit_id")
            Unit.delete().where(Unit.id == unit_id).execute()
            Department.update({Department.unit: None}).where(
                Department.unit == unit_id
            ).execute()
            flash(f"Unit deleted")

    units = Unit.select().group_by(Unit.name)
    return render_template("units_edit.html", units=units)


@app.route("/departments/")
@login_required
def departments():
    latest_test = (
        StructureTest.select(StructureTest.id, StructureTest.name)
        .order_by(StructureTest.id.desc())
        .get()
    )

    last_updated = Worker.select(fn.MAX(Worker.updated)).scalar()

    units = (
        Department.select(
            Department,
            Case(None, ((Unit.name.is_null(), "No Unit"),), Unit.name).alias(
                "unit_name"
            ),
            fn.count(Worker.id).alias("worker_count"),
            fn.sum(Case(Participation.structure_test, ((1, 1),), 0)).alias("members"),
            fn.sum(Case(Participation.structure_test, ((latest_test.id, 1),), 0)).alias(
                "latest"
            ),
        )
        .join(Unit, JOIN.LEFT_OUTER, on=(Department.unit == Unit.id))
        .join(Worker, JOIN.LEFT_OUTER, on=(Department.id == Worker.organizing_dept_id))
        .join(Participation, JOIN.LEFT_OUTER, on=(Worker.id == Participation.worker))
        .join(
            StructureTest,
            JOIN.LEFT_OUTER,
            on=(Participation.structure_test == StructureTest.id),
        )
        .where(Worker.updated == last_updated)
        .group_by(Department.id)
    )
    department_count = len(units)
    return render_template(
        "departments.html",
        latest_test_name=latest_test.name,
        units=units,
        department_count=department_count,
    )


@app.route("/department/")
@app.route("/department/<path:department_slug>", methods=["GET", "POST"])
@login_required
def department(department_slug=None):
    if request.method == "POST":
        # only admins can switch department alias
        if is_admin():
            Department.update(
                alias=request.form["alias"].strip() or None,
                unit=request.form["unit"] or None,
            ).where(Department.slug == department_slug).execute()
        flash("Department updated")

    if department_slug:
        department = Department.get(Department.slug == department_slug)
    else:
        department = Department.get(Department.id == session["department_id"])

    last_updated = Worker.select(fn.MAX(Worker.updated)).scalar()

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
            (
                (Worker.organizing_dept_id == department.id)
                | (Worker.department_id == department.id)
            )
            & (Worker.updated == last_updated)
        )
        .group_by(Worker.id)
        .order_by(Worker.updated.desc(), Worker.name, Participation.structure_test)
    )

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
    return jsonify(
        list(
            Participation.select(Participation, Worker.organizing_dept_id)
            .join(Worker, on=(Participation.worker == Worker.id))
            .dicts()
        )
    )


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


@app.route("/worker/", methods=["GET", "POST"])
@app.route("/worker/<int:worker_id>", methods=["GET", "POST"])
@login_required
def worker(worker_id=None):
    worker = None
    if request.method == "POST":
        data = dict(
            preferred_name=request.form.get("preferred_name", "").strip(),
            pronouns=request.form.get("pronouns", "").strip(),
            email=request.form.get("email", "").strip() or None,
            phone=request.form.get("phone", "").strip() or None,
            notes=request.form.get("notes", "").strip(),
            active=bool(request.form.get("active")),
        )
        # only admins can switch worker departments
        if is_admin():
            data["organizing_dept_id"] = request.form["organizing_dept"]

            if request.form.get("password"):
                if request.form.get("email"):
                    data["password"] = bcryptify(request.form["password"].strip())
                    data["dept_chair_id"] = request.form["organizing_dept"]
                    flash("Added as user")
                else:
                    flash("If setting a password a email address is required, too")

        if worker_id:
            Worker.update(**data).where(Worker.id == worker_id).execute()
            flash("Worker updated")
        else:
            worker = Worker.get_or_create(
                name=request.form.get("name", "").strip(),
                contract="manual",
                # special case for manually added worker
                department_id=0,
                **data,
                updated=date.today(),
                unit=0,
            )
            flash("Worker added")

        return redirect(
            url_for(
                "department",
                department_slug=Department.select(Department.slug)
                .where(Department.id == request.form["organizing_dept"])
                .scalar(),
            )
        )

    if worker_id:
        worker = Worker.get(Worker.id == worker_id)

    structure_tests = list(
        StructureTest.select(
            StructureTest.id,
            StructureTest.name,
            StructureTest.description,
            Participation.added,
        )
        .join(
            Participation,
            JOIN.LEFT_OUTER,
            on=(
                (StructureTest.id == Participation.structure_test)
                & (Participation.worker == worker_id)
            ),
        )
        .order_by(StructureTest.added)
        .dicts()
    )

    last_updated = Worker.select(fn.MAX(Worker.updated)).scalar()

    return render_template(
        "worker.html",
        worker=worker,
        structure_tests=structure_tests,
        Department=Department,
        last_updated=last_updated,
    )


@app.route("/users/", methods=["GET", "POST"])
@login_required
def users():
    if request.method == "POST":
        Worker.update(
            unit_chair_id=request.form["unit_chair_id"] or None,
        ).where(Worker.id == request.args.get("user_id")).execute()
        flash("User updated")

    users = list(
        Worker.select(Worker, Department.name.alias("department_name"))
        .join(Department, on=(Worker.organizing_dept_id == Department.id))
        .where(Worker.password.is_null(False))
        .dicts()
    )
    units = Unit.select().order_by(Unit.name)
    return render_template(
        "users.html", users=users, units=units, departments=departments
    )


@app.route("/participation/<int:worker_id>/<int:structure_test_id>/<int:status>")
def participation(worker_id, structure_test_id, status):
    worker = Worker.get(Worker.id == worker_id)
    if session.get("department_id") == worker.organizing_dept_id or is_admin():
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

    last_updated = Worker.select(fn.MAX(Worker.updated)).scalar()

    new_workers = (
        Worker.select(Worker, Department.name.alias("department_name"))
        .join(Department, on=(Worker.department_id == Department.id))
        .where((Worker.added == last_updated) & (Worker.department_id != 0))
    ).dicts()

    former_workers = (
        Worker.select(Worker, Department.name.alias("department_name"))
        .join(Department, on=(Worker.department_id == Department.id))
        .where((Worker.updated != last_updated) & (Worker.department_id != 0))
    ).dicts()

    flash(f"Found {len(new_workers)} new workers")

    return render_template(
        "upload_record.html",
        new_workers=new_workers,
        former_workers=former_workers,
    )


def parse_csv(csv_file_b):
    mapping = {}
    with open("mapping.yml") as mapping_file:
        mapping = yaml.safe_load(mapping_file)

    with io.TextIOWrapper(csv_file_b, encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=";")

        for row in reader:
            department_name = mapping["mapping"].get(row["Sect Desc"], row["Sect Desc"])
            department, _ = Department.get_or_create(
                # name=row["Job Sect Desc"].title(),
                # slug=slugify(row["Job Sect Desc"]),
                name=department_name.title(),
                slug=slugify(department_name),
            )

            worker_name = f"{row['Last']},{row['First Name']}"
            if row["Middle"]:
                worker_name += f" {row['Middle']}"

            worker = Worker.get_or_none(
                name=worker_name,
            )

            if not worker:
                worker = Worker.create(
                    # name=row["Name"],
                    name=worker_name,
                    department_id=department.id,
                    organizing_dept_id=department.id,
                    # default organizing_dept to department ID, can be changed later on
                    # unit=row["Unit"],
                )

            worker.update(
                updated=date.today(),
                contract=row["Job Code"],
                unit=row["Campus"],
                department_id=department.id,
            ).where(
                Worker.id == worker.id,
            ).execute()


if __name__ == "__main__":
    if not Path(DATABASE).exists():
        create_tables()

    app.run(port=5001)
