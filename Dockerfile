FROM python:slim

RUN pip install poetry gunicorn

WORKDIR /app/

COPY poetry.lock pyproject.toml ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

COPY ./wallchart/ ./wallchart/

COPY ./mapping.yml .

COPY ./app.py .

CMD ["gunicorn"  , "-b", "0.0.0.0:8000", "app"]

EXPOSE 8000
