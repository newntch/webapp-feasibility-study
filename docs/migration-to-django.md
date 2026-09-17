# Django and PostgreSQL migration

The new local stack uses two PostgreSQL databases on one PostgreSQL server:
`application_db` for Django-managed app tables, and `clinical_db` for the
read-only OMOP queries. The clinical importer uses a separate write role. The
source remains the local EHRShot OMOP v5.3.1 DuckDB snapshot and the JSON files
under `data/`. Do not put identifiable clinical data in this repository.

## First local run

1. Ensure the DuckDB file exists at
   `data/omop/ehrshot_omop/ehrshot_omop.duckdb` and that `data/users.json`
   contains the intended local accounts. Keep a separate copy of the source
   files before migration.
2. Set `DJANGO_SECRET_KEY`, `APP_DB_PASSWORD`, `CLINICAL_DB_PASSWORD`,
   `CLINICAL_IMPORT_DB_PASSWORD`, and `POSTGRES_PASSWORD` in a local `.env`.
   Compose's checked-in defaults are for an isolated development machine only.
3. Start the database and create the app tables:

   ```bash
   docker compose up -d postgres
   docker compose build web
   docker compose run --rm web /app/.venv/bin/python manage.py migrate --noinput
   ```

4. Review source shape, then import the clinical and app data:

   ```bash
   docker compose run --rm web /app/.venv/bin/python manage.py import_clinical_duckdb --dry-run
   docker compose run --rm web /app/.venv/bin/python manage.py import_app_json --source-dir data --dry-run
   docker compose run --rm web /app/.venv/bin/python manage.py import_clinical_duckdb
   docker compose run --rm web /app/.venv/bin/python manage.py import_app_json --source-dir data
   docker compose up -d web
   ```

5. Open <http://127.0.0.1:4173>. `/api/health` returns HTTP 200 after both
   databases are ready. Users must sign in again; old sessions and pending OTPs
   are not imported.

The clinical command copies all 12 tables in bounded batches. Each table is
committed separately, so an interrupted import can resume. A nonempty target
table with a different row count stops the import. The final metadata record
stores the source schema fingerprint, CDM version, vocabulary versions, and
completion time. Cohort queries are unavailable until that record exists.
The app import is transactional and idempotent for records with the same IDs.

## Validation

Run `uv run pytest -q` for Django, dictionary synchronization, and browser
module serving tests. Compare selected cohort
counts and attrition with the DuckDB adapter before using the new backend for
research. Check row counts and indexes in `clinical_db`; review the clinical
data quality caveats in [OMOP adapter](design/omop-cdm-adapter.md). SQL preview
uses placeholders because the live query binds values separately.

For a restore rehearsal, back up each database with `pg_dump -Fc`, restore into
new database names, and compare row counts and `/api/health` before relying on
the backups. Do not remove the DuckDB and JSON sources during validation. For
local rollback, restore the separate database backups and redeploy a previously
validated Django image; there is no second application server.

## Operational boundaries

The app's clinical connection can only read. Django migrations target
`application_db`; the clinical importer owns `clinical_db` schema and loading.
No cross-database foreign keys or transactions are used. The local Compose
configuration is not a production deployment recipe: production needs managed
secrets, HTTPS, scheduled backups, restore drills, SMTP, monitored query time,
and a controlled data refresh/cutover procedure.
