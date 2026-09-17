# PostgreSQL-only cutover

The application uses `application_db` for Django-managed records and
`clinical_db` for OMOP CDM v5.3.1 data. It does not import application JSON,
DuckDB, or a local dictionary file at runtime.

## Verify before removing a legacy source

Start PostgreSQL, then verify `clinical_db` contains the query tables
`person`, `concept`, `condition_occurrence`, `measurement`, `drug_exposure`,
`visit_occurrence`, and `cdm_source`; verify `cdm_source.cdm_version` is
`v5.3.1`; and check `/api/health` after starting the web service. Check that
`application_db` contains its Django migrations and existing application data.

Back up each database before a cutover:

```bash
mkdir -p temp/backups
docker compose exec -T postgres pg_dump -U postgres -Fc clinical_db > temp/backups/clinical_db.dump
docker compose exec -T postgres pg_dump -U postgres -Fc application_db > temp/backups/application_db.dump
pg_restore -l temp/backups/clinical_db.dump
pg_restore -l temp/backups/application_db.dump
```

Keep backups outside version control. Restore with `pg_restore` into the target
database before starting the application. Do not remove a source dataset until
the restored clinical database has passed the OMOP and health checks.
