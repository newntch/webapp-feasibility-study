# Deployment and storage

The local `compose.yaml` starts PostgreSQL and the Django/Gunicorn web image.
It creates two independent databases on one PostgreSQL instance:

- `application_db`: Django migrations own the schema; users, sessions, OTPs,
  saved cohorts, and audit records live here.
- `clinical_db`: the importer owns the OMOP schema. The web role reads it but
  cannot mutate it. Cohort queries use bound SQL parameters.

Build and run the local stack with `docker compose build web` and
`docker compose up -d`. Check `/api/health` after the database and import steps
in [the migration guide](migration-to-django.md). `docker compose ps` shows
service health. The frontend is plain browser JavaScript delivered by Django;
the image contains no JavaScript server or build toolchain.

This Compose file is a development configuration, not a production recipe.
Before production, provide HTTPS, secure cookies and CSRF origins, managed
secrets, a least-privilege database setup, SMTP, backups of both databases,
restore drills, and query-time monitoring. Keep clinical data out of logs and
repository fixtures. Preserve the source snapshot and import metadata for
provenance; do not replace a clinical dataset without a validated refresh and
cutover process.
