import csv
from datetime import date, timedelta
from functools import wraps
from io import TextIOWrapper

import bcrypt
import yaml
from flask import redirect, session, url_for
from peewee import fn
from slugify import slugify

from wallchart.db import Department, Worker


def max_age():
    return date.today() - timedelta(days=365)


def last_updated():
    return (
        Worker.select(fn.MAX(Worker.updated))
        .where(Worker.contract != "manual")
        .scalar()
    )


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


def parse_csv(csv_file_b):
    mapping = {}
    with open("mapping.yml") as mapping_file:
        mapping = yaml.safe_load(mapping_file)

    with TextIOWrapper(csv_file_b, encoding="utf-8") as csv_file:
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

    Worker.update(active=False).where(Worker.updated != date.today()).execute()
