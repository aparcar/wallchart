from datetime import date

from playhouse.migrate import *

db = SqliteDatabase("wallcharts.db")
migrator = SqliteMigrator(db)

# migrate(migrator.add_column("Department", "alias", CharField(unique=True, null=True)))

migrate(migrator.add_column("Participation", "added", DateField(default=date.today)))
migrator.add_index("Participation", ("worker", "structure_test"), True),
