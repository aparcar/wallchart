from flask import Blueprint, jsonify
from playhouse.flask_utils import get_object_or_404

from wallchart.db import Department, Participation, Unit, Worker
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


@api.route("/worker/<int:worker_id>")
@login_required
def api_worker(worker_id):
    workers = (
        Worker.select(
            Worker,
            Department.slug.alias("department_slug"),
            Department.name.alias("department_name"),
        )
        .join(Department, on=(Worker.organizing_dept_id == Department.id))
        .dicts()
    )

    worker = get_object_or_404(workers, (Worker.id == worker_id))
    return jsonify(worker)


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


@api.route("/units")
@login_required
def api_units():
    return jsonify(list(Unit.select().dicts()))
