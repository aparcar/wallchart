from wallchart.app import app, database

from wallchart.models import *
from wallchart.views import *

def create_tables():
    with database:
        database.create_tables([Unit, Department, Worker, StructureTest, Participation])

create_tables()
