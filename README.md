# Diagnosis Feasibility Study Webapp

Django application for OMOP cohort feasibility. PostgreSQL keeps clinical
data and application data in separate databases. The browser uses plain
JavaScript modules; no JavaScript package manager or server runtime is needed.

## Requirements

- Python 3.12 or newer and `uv`
- Docker Compose for the local PostgreSQL databases
- PostgreSQL backups containing the OMOP CDM v5.3.1 clinical dataset and application data

## Run locally

Follow [the PostgreSQL-only cutover guide](docs/postgres-only-cutover.md) to
configure secrets and restore or initialize the two databases. Then:

```bash
docker compose up -d --build
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
run `uv run python manage.py migrate`, provision the local demo account with
`DEMO_ACCOUNT_ENABLED=1 uv run python manage.py ensure_demo_user`, and then
run `uv run python manage.py runserver 4173`.

## Documentation

- [Setup and configuration](docs/setup-and-configuration.md)
- [Deployment and storage](docs/deployment-and-storage.md)
- [PostgreSQL-only cutover](docs/postgres-only-cutover.md)
- [Product and usage](docs/product-and-usage.md)
- [Current architecture](docs/design/project-overview.md)
- [OMOP CDM adapter](docs/design/omop-cdm-adapter.md)
