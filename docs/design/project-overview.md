# Current architecture

The browser loads HTML, CSS, and plain JavaScript modules from Django. The
JavaScript handles filter editing and presentation; Django owns authentication,
API validation, saved cohorts, audit logs, and clinical query execution.

```text
Browser ──HTTPS/API──> Django/Gunicorn ──read/write──> application_db
                           │
                           └────────read-only────────> clinical_db (OMOP)

DuckDB snapshot ──one-time, versioned import──────────> clinical_db
Legacy app JSON ──one-time, idempotent import──────────> application_db
```

`application_db` and `clinical_db` are separate PostgreSQL databases with
different roles. There are no cross-database foreign keys or transactions.
The clinical importer records the source schema fingerprint, OMOP CDM version,
vocabulary versions, row counts, and completion time. Cohort execution fails
closed until that metadata is present. The import source is treated as
synthetic/de-identified research data; no identifiable patient fixtures belong
in this repository.

See [the migration guide](../migration-to-django.md) for setup and operational
boundaries, and [the OMOP adapter](omop-cdm-adapter.md) for query mapping.
