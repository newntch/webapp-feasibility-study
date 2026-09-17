# Setup and configuration

The application runs on Django and uses two PostgreSQL databases. `application_db`
holds users, sessions, saved cohorts, and audit runs. `clinical_db` holds OMOP
tables and import metadata. The web account only has read access to the
clinical database. The clinical importer uses a separate write account.

Use a local `.env` for Compose secrets. Do not commit it or clinical data. At a
minimum, set `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `APP_DB_PASSWORD`,
`CLINICAL_DB_PASSWORD`, and `CLINICAL_IMPORT_DB_PASSWORD`. The defaults in
`compose.yaml` are only for isolated local development.

The Django environment variables are:

| Area | Variables |
| --- | --- |
| App DB | `APP_DB_HOST`, `APP_DB_PORT`, `APP_DB_NAME`, `APP_DB_USER`, `APP_DB_PASSWORD` |
| Clinical DB | `CLINICAL_DB_HOST`, `CLINICAL_DB_PORT`, `CLINICAL_DB_NAME`, `CLINICAL_DB_USER`, `CLINICAL_DB_PASSWORD` |
| Clinical import | `CLINICAL_IMPORT_DB_USER`, `CLINICAL_IMPORT_DB_PASSWORD` |
| Django | `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `COOKIE_SECURE` |
| Email | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SMTP_SECURE` |
| Google sign-in | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `GOOGLE_ALLOWED_EMAILS` |
| Clinical provenance | `CLINICAL_DATASET_VERSION` |

See [the migration guide](migration-to-django.md) for the first-run command
sequence. The source DuckDB and legacy JSON files under `data/` are only used
for the initial imports. They are mounted read-only in the web container.
Users must sign in again after migration because sessions and pending OTPs
are not imported.

For password changes, use Django's password-reset flow or
`uv run python manage.py changepassword <email>` with the app database
configured. No password-hash generation script is needed.

The four public pages and their browser JavaScript modules are served by
Django. No build step is required for these assets.
