# Wallchart

This repository contains a tool to manage (student) union members and track
digital wall charts. It's specifically crafted for the University of Hawaii,
Manoa but could be modified for a more general purpose.

The technology is based on Python using the Flask web framework.

## Installation

The tool uses `poetry` and is therefore trivially to install. If `poetry` is
not yet installed on the system, do so by running the following command.

	pip install poetry

To install `wallchart` just use `pip`

	pip install wallchart

Now all dependencies should be in place and it's possible to either run
`wallchart` or start developing. Next you should create a `config.py` file
which contains both an admin password as well as an application secret (used to
encrypt cookies).

A `config.py` file should contain at least the following settings:

	ADMIN_PASSWORD = "changeme"
	SECRET_KEY = "changeme"

Optionally define `DATABASE` if you don't like the sqlite database at `./wallchart.db`.

## Running

To run `wallchart` you may use `gunicorn` to allow multiple connections at once
(i.e. multiple people use it at the same time). Install `gunicorn` using the
command below.

	poetry add gunicorn

To run `wallchart` execute the following command.

	poetry shell
	gunicorn

You'll find the web interface at http://localhost:8000

## Development

Get the source code

	git clone https://github.com/aparcar/wallchart.git
	cd wallchart/
	poetry install

For development you may use the internal Flask web server which automatically
reloads files after modification.

	poetry shell
	export FLASK_DEBUG=1
	flask run

After changing things, don't forget to see if all tests still pass.

	poetry shell
	pytest
