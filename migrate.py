from playhouse.migrate import *
from datetime import date
from main import Department, Unit

db = SqliteDatabase("wallcharts.db")
migrator = SqliteMigrator(db)

# migrate(migrator.add_column("Department", "alias", CharField(unique=True, null=True)))

# migrate(migrator.add_column("Participation", "added", DateField(default=date.today)))
# migrator.add_index("Participation", ("worker", "structure_test"), True),

migrate(migrator.add_column("Worker", "password", TextField(null=True)))
migrate(
    migrator.add_column(
        "Worker",
        "unit_chair_id",
        ForeignKeyField(Unit, field=Unit.id, backref="chairs", null=True),
    )
)
migrate(
    migrator.add_column(
        "Worker",
        "dept_chair_id",
        ForeignKeyField(Department, field=Department.id, backref="chairs", null=True),
    )
)
