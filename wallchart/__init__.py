import os

from flask import Flask
from playhouse.flask_utils import FlaskDB

__version__ = "0.1.0"

db_wrapper = FlaskDB()


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object("wallchart.defaults")
    app.config.from_pyfile("config.py", silent=True)

    app.config["DATABASE"] = f"sqlite:///{app.instance_path}/wallcharts.db"

    if config is not None:
        if isinstance(config, dict):
            app.config.update(config)
        elif config.endswith(".py"):
            app.config.from_pyfile(config)

    assert (
        app.secret_key != "changeme"
    ), f"Change flask secret in {app.instance_path }/config.py"

    assert (
        app.config["ADMIN_PASSWORD"] != "changeme"
    ), f"Change admin password in {app.instance_path}/config.py"

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from wallchart.db import db

    app.register_blueprint(db)

    db_wrapper.init_app(app)

    from wallchart.views import views

    app.register_blueprint(views)

    from wallchart.api import api

    app.register_blueprint(api)

    return app
