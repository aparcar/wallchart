from playhouse.migrate import *
from datetime import date
from main import Department, Unit, Worker

db = SqliteDatabase("wallcharts.db")
migrator = SqliteMigrator(db)

# migrate(migrator.add_column("Department", "alias", CharField(unique=True, null=True)))

# migrate(migrator.add_column("Participation", "added", DateField(default=date.today)))
# migrator.add_index("Participation", ("worker", "structure_test"), True),

# migrate(migrator.add_column("Worker", "password", TextField(null=True)))
# migrate(
#    migrator.add_column(
#        "Worker",
#        "unit_chair_id",
#        ForeignKeyField(Unit, field=Unit.id, backref="chairs", null=True),
#    )
# )
# migrate(
#    migrator.add_column(
#        "Worker",
#        "dept_chair_id",
#        ForeignKeyField(Department, field=Department.id, backref="chairs", null=True),
#    )
# )

Worker.delete().where(Worker.id == 1142).execute()
Worker.delete().where(Worker.id == 648).execute()
Worker.delete().where(Worker.id == 1289).execute()

migrate(
    migrator.drop_not_null("Worker", "organizing_dept_id"),
    migrator.drop_not_null("Worker", "unit"),
    migrator.drop_not_null("Worker", "contract"),
    migrator.drop_not_null("Worker", "department_id"),
    migrator.add_index("Worker", ("name",), True),
)
