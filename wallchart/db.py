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
    contract = CharField()
    unit = CharField()
    department_id = IntegerField()
    organizing_dept_id = IntegerField()
    unit_chair_id = ForeignKeyField(Unit, field=Unit.id, backref="chairs", null=True)
    dept_chair_id = ForeignKeyField(
        Department, field=Department.id, backref="chairs", null=True
    )
    active = BooleanField(default=True)
    added = DateField(default=date.today)
    updated = DateField(default=date.today)
    password = CharField(null=True)

    class Meta:
        indexes = ((("name", "unit", "department_id", "contract"), True),)


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

