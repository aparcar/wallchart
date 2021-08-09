from playhouse.migrate import *

db = SqliteDatabase("wallcharts.db")
migrator = SqliteMigrator(db)

migrate(
    migrator.add_column('Department', 'alias', CharField(unique=True, null=True))
)