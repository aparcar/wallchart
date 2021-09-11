from flask import Blueprint, jsonify

from wallchart.db import Department, Participation, Worker
from wallchart.util import login_required

api = Blueprint("api", __name__, url_prefix="/api")


@api.route("/workers")
@login_required
def api_workers():
    return jsonify(
        list(
            Worker.select(
                Worker,
                Department.slug.alias("department_slug"),
                Department.name.alias("department_name"),
            )
            .join(Department, on=(Worker.organizing_dept_id == Department.id))
            .dicts()
        )
    )


@api.route("/participation")
@login_required
def api_participation():
    return jsonify(
        list(
            Participation.select(Participation, Worker.organizing_dept_id)
            .join(Worker, on=(Participation.worker == Worker.id))
            .dicts()
        )
    )


@api.route("/departments")
@login_required
def api_departments():
    return jsonify(list(Department.select().dicts()))
