from datetime import date

import bcrypt
import phonenumbers
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from peewee import JOIN, Case, fn
from playhouse.flask_utils import get_object_or_404
from slugify import slugify

from wallchart.db import Department, Participation, StructureTest, Unit, Worker
from wallchart.util import (
    bcryptify,
    is_admin,
    last_updated,
    login_required,
    max_age,
    parse_csv,
)

views = Blueprint("", __name__, url_prefix="/")


@views.route("/login/", methods=["GET", "POST"])
def login():
    status = 200
    if request.method == "POST" and request.form["email"]:
        if (
            request.form["email"] == "admin"
            and request.form["password"] == current_app.config["ADMIN_PASSWORD"]
        ):
            session["logged_in"] = True
            session["user_id"] = 0
            session["department_id"] = 0
            session["admin"] = True
            flash("You are logged in as administrator.")
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


@views.route("/")
def homepage():
    if session.get("logged_in"):
        if is_admin():
            return redirect(url_for("admin"))
        else:
            return redirect(url_for("department"))
    else:
        return redirect(url_for("login"))


@views.route("/download_db")
@login_required
def download_db():
    return send_file(
        current_app.config["DATABASE"][len("sqlite:///") :],
        download_name=f"wallcharts-backup-{date.today().strftime('%Y-%m-%d')}.db",
    )


@views.route("/admin")
@login_required
def admin():
    department_count = Department.select(fn.count(Department.id)).scalar()
    worker_count = (
        Worker.select(fn.count(Worker.id)).where(Worker.active == True).scalar()
    )
    return render_template(
        "admin.html",
        last_updated=last_updated(),
        department_count=department_count,
        worker_count=worker_count,
    )


@views.route("/structure_test", methods=["GET", "POST"])
@views.route("/structure_test/<int:structure_test_id>", methods=["GET", "POST"])
@login_required
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


@views.route("/find_worker")
@login_required
def find_worker():
    return render_template("find_worker.html")


@views.route("/units/")
@login_required
def units_view():
    latest_test = (
        StructureTest.select(StructureTest.id, StructureTest.name)
        .order_by(StructureTest.id.desc())
        .get()
    )

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
        .where(Worker.active == True)
        .group_by(Unit.id)
    )
    return render_template("units.html", units=units, latest_test_name=latest_test.name)


@views.route("/manage-units/", methods=["GET", "POST"])
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
            flash("Unit deleted")

    units = Unit.select().group_by(Unit.name)
    return render_template("units_edit.html", units=units)


@views.route("/departments/")
@login_required
def departments():
    latest_test = (
        StructureTest.select(StructureTest.id, StructureTest.name)
        .order_by(StructureTest.id.desc())
        .get()
    )

    units = (
        Department.select(
            Department,
            Case(None, ((Unit.name.is_null(), "No Unit"),), Unit.name).alias(
                "unit_name"
            ),
            # select `none` as entry to calculate the total number of workers.
            # It's a LEFT JOIN so all workers are selected, however if they
            # participated in both structure tests they appear twice. This
            # means a simple count is not possible since the numbers would be
            # off. Instead count how many people did not participate in any
            # test and add it to the with highest participation.
            # Reminder: 0 or 1 participations result in 1 row (left join), two
            # participations result in two row.
            fn.sum(Case(None, ((Participation.structure_test.is_null(), 1),), 0)).alias(
                "none"
            ),
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
        .where(Worker.active == True)
        .group_by(Department.id)
    )
    department_count = len(units)
    return render_template(
        "departments.html",
        latest_test_name=latest_test.name,
        units=units,
        department_count=department_count,
    )


@views.route("/department/")
@views.route("/department/<path:department_slug>", methods=["GET", "POST"])
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

    workers_active = (
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
            ((Worker.organizing_dept_id == department.id))
            & (Worker.updated > max_age())
            & (Worker.active == True)
        )
        .group_by(Worker.id)
        .order_by(Worker.active.desc(), Worker.name, Participation.structure_test)
    )
    workers_inactive = (
        Worker.select(Worker)
        .where(
            (Worker.organizing_dept_id == department.id)
            & (Worker.department_id == department.id)
            & (Worker.updated > max_age())
            & (Worker.active == False)
        )
        .group_by(Worker.id)
        .order_by(Worker.active.desc(), Worker.name)
    )

    workers_external = (
        Worker.select(Worker)
        .where(
            (Worker.organizing_dept_id != department.id)
            & (Worker.department_id == department.id)
            & (Worker.updated > max_age())
            & (Worker.active == False)
        )
        .group_by()
        .order_by(Worker.active.desc(), Worker.name)
    )

    units = Unit.select().order_by(Unit.name)

    structure_tests = StructureTest.select().order_by(StructureTest.added)

    return render_template(
        "department.html",
        workers_active=workers_active,
        workers_inactive=workers_inactive,
        workers_external=workers_external,
        department=department,
        structure_tests=structure_tests,
        last_updated=last_updated(),
        units=units,
    )


@views.route("/structure_tests", methods=["GET", "POST"])
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


@views.route("/worker/<int:worker_id>/delete")
@login_required
def worker_delete(worker_id):
    worker = get_object_or_404(Worker, (Worker.id == worker_id))
    Worker.delete().where(Worker.id == worker_id).execute()
    Participation.delete().where(Participation.worker == worker_id).execute()
    flash(f"Deleted worker {worker.name} ({worker.id})")
    return redirect(url_for("homepage"))


@views.route("/worker/", methods=["GET", "POST"])
@views.route("/worker/<int:worker_id>", methods=["GET", "POST"])
@login_required
def worker(worker_id=None):
    worker = None
    if request.method == "POST":
        data = dict(
            preferred_name=request.form.get("preferred_name", "").strip(),
            pronouns=request.form.get("pronouns", "").strip(),
            email=request.form.get("email", "").strip() or None,
            notes=request.form.get("notes", "").strip(),
            active=bool(request.form.get("active")),
        )

        phone = request.form.get("phone")
        try:
            if phone:
                data["phone"] = phonenumbers.format_number(
                    phonenumbers.parse(phone, "US"),
                    phonenumbers.PhoneNumberFormat.NATIONAL,
                )
        except:
            flash(f"Phone number '{phone}' is not a correct phone number", "danger")

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

    return render_template(
        "worker.html",
        worker=worker,
        structure_tests=structure_tests,
        Department=Department,
        last_updated=last_updated(),
    )


@views.route("/user/<int:user_id>/delete")
@login_required
def user_delete(user_id):
    user = get_object_or_404(Worker, (Worker.id == user_id))
    Worker.update({Worker.password: None}).where(Worker.id == user_id).execute()
    flash(f"Deleted user password of {user.name} ({user.id})")
    return redirect(url_for("users"))


@views.route("/users/", methods=["GET", "POST"])
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
        .order_by(Worker.name)
        .dicts()
    )
    units = Unit.select().order_by(Unit.name)
    return render_template(
        "users.html", users=users, units=units, departments=departments
    )


@views.route("/former/")
@login_required
def former():
    former = list(
        Worker.select(Worker, Department.name.alias("department_name"))
        .join(Department, on=(Worker.organizing_dept_id == Department.id))
        .where(Worker.active != True)
        .order_by(Worker.name)
        .dicts()
    )
    return render_template("former.html", former=former)


@views.route("/participation/<int:worker_id>/<int:structure_test_id>/<int:status>")
@login_required
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


@views.route("/logout/")
def logout():
    session.clear()
    flash("You were logged out")
    return redirect(url_for("homepage"))


@views.route("/upload_record", methods=["GET", "POST"])
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
            flash("Wrong filetype, convert to CSV please")
            return redirect(request.url)

        if record:
            parse_csv(record)

    new_workers = (
        Worker.select(Worker, Department.name.alias("department_name"))
        .join(Department, on=(Worker.department_id == Department.id))
        .where((Worker.added == last_updated()) & (Worker.department_id != 0))
    ).dicts()

    if new_workers:
        flash(f"Found {len(new_workers)} new workers")

    return render_template(
        "upload_record.html",
        new_workers=new_workers,
    )
