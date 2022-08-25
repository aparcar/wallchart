import os

from flask import Flask
from playhouse.flask_utils import FlaskDB
from pathlib import Path

__version__ = "0.1.0"

db_wrapper = FlaskDB()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object("wallchart.defaults")

    if test_config is None:
        # look for a config file in these places
        config_locations = [
            Path.cwd(),
            Path.home() / ".config/wallchart",
            Path("/etc/wallchart"),
        ]
        for path in config_locations:
            if (path / "config.py").exists():
                app.config.from_pyfile(path / "config.py")
                print(f"Config loaded from {path}/config.py")
                break
    else:
        # load a test_config in for unit testing
        if isinstance(test_config, dict):
            app.config.update(test_config)
        elif test_config.endswith(".py"):
            app.config.from_pyfile(test_config)

    app.config["DATABASE"] = f"sqlite:///{app.config['DATABASE']}"

    assert app.secret_key != "changeme", f"Please change SECRET_KEY in config.py"

    assert (
        app.config["ADMIN_PASSWORD"] != "changeme"
    ), f"Please change ADMIN_PASSWORD in config.py"

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
