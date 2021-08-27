import os

from flask import Flask
from peewee import SqliteDatabase
import configparser
import logging

config = configparser.ConfigParser()
config.read("wallchart/config.ini")

# database = SqliteDatabase('wallcharts.db')

# create and configure the app
app = Flask(__name__, instance_relative_config=True)

# load the instance config, if it exists, when not testing
# app.config.from_pyfile('config.ini', silent=False)

app.config.from_mapping(
    DATABASE = os.path.join(app.instance_path, config["database"]["path"]),
    SECRET_KEY = config["flask"]["secret"]
)

assert app.config["SECRET_KEY"] != "changeme", "Change flask secret in config.ini"

assert config["admin"]["password"] != "changeme", "Change admin password in config.ini"


# ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

logger = logging.getLogger("peewee")
logger.addHandler(logging.StreamHandler())
logger.setLevel(config["logging"]["level"])

database = SqliteDatabase(app.config["DATABASE"])
