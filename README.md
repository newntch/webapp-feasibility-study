# Diagnosis Feasibility Study Webapp

Django application for OMOP cohort feasibility. PostgreSQL keeps clinical
data and application data in separate databases. The browser uses plain
JavaScript modules; no JavaScript package manager or server runtime is needed.

## Requirements

- Python 3.12 or newer and `uv`
- Docker Compose for the local PostgreSQL databases
- The EHRShot OMOP v5.3.1 DuckDB source for a first clinical import

## Run locally

Follow [the migration and first-run guide](docs/migration-to-django.md) to
configure secrets, initialize the databases, and import the source data. Then:

```bash
docker compose up -d
```

Open <http://127.0.0.1:4173>. The browser assets are served by Django.

## Development and checks

```bash
uv sync
uv run pytest -q
uv run ruff check src tests/django
uv run ruff format --check src tests/django
```

To run Django outside the web container against a reachable PostgreSQL server,
set the database environment variables in [setup and configuration](docs/setup-and-configuration.md)
and run `uv run python manage.py runserver 4173`.

`uv run python manage.py sync_dictionary` refreshes the local dictionary
snapshot from its published CSV sources. This command needs network access;
the web service does not need it to serve an existing snapshot.

## Documentation

- [Setup and configuration](docs/setup-and-configuration.md)
- [Deployment and storage](docs/deployment-and-storage.md)
- [Django and PostgreSQL migration](docs/migration-to-django.md)
- [Product and usage](docs/product-and-usage.md)
- [Current architecture](docs/design/project-overview.md)
- [OMOP CDM adapter](docs/design/omop-cdm-adapter.md)
