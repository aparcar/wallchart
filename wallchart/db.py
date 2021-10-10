from datetime import date

from flask import Blueprint, current_app
from peewee import (
    AutoField,
    BooleanField,
    CharField,
    DateField,
    ForeignKeyField,
    IntegerField,
    TextField,
)

from wallchart import db_wrapper

db = Blueprint("db", __name__)


class Unit(db_wrapper.Model):
    id = AutoField()
    name = CharField(unique=True)
    slug = CharField()


class Department(db_wrapper.Model):
    id = AutoField()
    name = CharField(unique=True)
    slug = CharField()
    alias = CharField(unique=True, null=True)
    unit = ForeignKeyField(Unit, backref="departments", null=True)


class Worker(db_wrapper.Model):
    id = AutoField()
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
        indexes = ((("name",), True),)


class StructureTest(db_wrapper.Model):
    id = AutoField()
    name = CharField(unique=True)
    description = TextField()
    active = BooleanField(default=True)
    added = DateField(default=date.today)


class Participation(db_wrapper.Model):
    worker = ForeignKeyField(Worker, field="id")
    structure_test = ForeignKeyField(StructureTest)
    added = DateField(default=date.today)

    class Meta:
        indexes = ((("worker", "structure_test"), True),)


def create_tables():
    with db_wrapper.database.connection_context():
        db_wrapper.database.create_tables(
            [Unit, Department, Worker, StructureTest, Participation]
        )
        department, _ = Department.get_or_create(
            id=0,
            name="Admin",
            slug="admin",
        )


def close():
    if not db_wrapper.database.is_closed():
        db_wrapper.database.close()


@db.cli.command("create-tables")
def cli_create_tables():
    print("Creating database tables...")
    with current_app.app_context():
        create_tables()
    print("Done")
