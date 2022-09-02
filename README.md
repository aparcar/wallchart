# Wallchart

This repository contains a tool to manage (student) union members and track
digital wall charts. It's specifically crafted for the University of Hawaii,
Manoa but could be modified for a more general purpose.

The technology is based on Python using the Flask web framework.

## Installation

The tool uses `poetry` and is therefore trivially to install. If `poetry` is
not yet installed on the system, do so by running the following command.

	pip install poetry

To install `wallchart` clone this repository and make `poetry` install all dependencies.

	git clone https://github.com/aparcar/wallchart.git
	cd wallchart/
	poetry install

Now all dependencies should be in place and it's possible to either run
`wallchart` or start developing. Next you should create a `config.py` file
which contains both an admin password as well as an application secret (used to
encrypt cookies).

	mkdir instance/
	cp wallchart/defaults.py instance/config.py

Modify both variables `ADMIN_PASSWORD` and `SECRET_KEY` else `wallchart`
refuses to start.

## Running

To run `wallchart` you may use `gunicorn` to allow multiple connections at once
(i.e. multiple people use it at the same time). Install `gunicorn` using the
command below.

	poetry add gunicorn

To run `wallchart` execute the following command.

	poetry shell
	flask db create-tables
	gunicorn

You'll find the web interface at http://localhost:8000

## Development

For development you may use the internal Flask web server which automatically
reloads files after modification.

	poetry shell
	export FLASK_DEBUG=1
	flask db create-tables
	flask run

After changing things, don't forget to see if all tests still pass.

	poetry shell
	pytest
