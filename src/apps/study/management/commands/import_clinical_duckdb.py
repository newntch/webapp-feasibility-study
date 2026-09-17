import hashlib
import json
import os
from pathlib import Path

import duckdb
import psycopg
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from psycopg import sql

TABLES = (
    "care_site",
    "cdm_source",
    "concept",
    "concept_ancestor",
    "condition_occurrence",
    "drug_exposure",
    "measurement",
    "person",
    "procedure_occurrence",
    "provider",
    "visit_detail",
    "visit_occurrence",
)
TYPE_MAP = {
    "BIGINT": "bigint",
    "INTEGER": "integer",
    "DOUBLE": "double precision",
    "DATE": "date",
    "TIMESTAMP": "timestamp",
    "VARCHAR": "text",
}
INDEXES = {
    "person": ("person_id",),
    "condition_occurrence": ("person_id", "condition_concept_id", "condition_start_date"),
    "measurement": ("person_id", "measurement_concept_id", "measurement_date"),
    "drug_exposure": ("person_id", "drug_concept_id", "drug_exposure_start_date"),
    "visit_occurrence": ("visit_occurrence_id", "person_id"),
    "concept": ("concept_id",),
}
PRIMARY_KEYS = {
    "care_site": ("care_site_id",),
    "concept": ("concept_id",),
    "concept_ancestor": ("ancestor_concept_id", "descendant_concept_id"),
    "condition_occurrence": ("condition_occurrence_id",),
    "drug_exposure": ("drug_exposure_id",),
    "measurement": ("measurement_id",),
    "person": ("person_id",),
    "procedure_occurrence": ("procedure_occurrence_id",),
    "provider": ("provider_id",),
    "visit_detail": ("visit_detail_id",),
    "visit_occurrence": ("visit_occurrence_id",),
}


def columns_for(source, table):
    rows = source.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = ? ORDER BY ordinal_position",
        [table],
    ).fetchall()
    if not rows or any(kind not in TYPE_MAP for _, kind in rows):
        raise CommandError(f"Unexpected schema in {table}")
    return rows


def schema_fingerprint(schema):
    return hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()


def import_table(source, target, table, columns, batch_size):
    names = [name for name, _ in columns]
    definition = sql.SQL(", ").join(
        sql.SQL("{} {}").format(sql.Identifier(name), sql.SQL(TYPE_MAP[kind]))
        for name, kind in columns
    )
    create = sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(sql.Identifier(table), definition)
    with target.cursor() as cursor:
        cursor.execute(create)
        cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
        existing = cursor.fetchone()[0]
    source_count = source.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    if existing:
        if existing != source_count:
            raise CommandError(f"Existing {table} row count differs from source")
        return source_count
    if source_count == 0:
        return 0

    result = source.execute(f'SELECT * FROM "{table}"')
    copy = sql.SQL("COPY {} ({}) FROM STDIN").format(
        sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, names))
    )
    with target.cursor() as cursor, cursor.copy(copy) as stream:
        while rows := result.fetchmany(batch_size):
            for row in rows:
                stream.write_row(row)
    with target.cursor() as cursor:
        cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
        loaded = cursor.fetchone()[0]
    if loaded != source_count:
        raise CommandError(f"Imported {table} row count differs from source")
    return loaded


class Command(BaseCommand):
    help = "Copy the 12 EHRShot OMOP v5.3.1 tables from DuckDB into clinical_db."

    def add_arguments(self, parser):
        parser.add_argument("--source", default="data/omop/ehrshot_omop/ehrshot_omop.duckdb")
        parser.add_argument("--batch-size", type=int, default=10000)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        path = Path(options["source"])
        if not path.is_file():
            raise CommandError(f"DuckDB source does not exist: {path}")
        source = duckdb.connect(str(path), read_only=True)
        try:
            actual = {
                row[0]
                for row in source.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'"
                ).fetchall()
            }
            if actual != set(TABLES):
                raise CommandError(
                    "OMOP source table set differs from the supported 12-table snapshot"
                )
            versions = source.execute("SELECT DISTINCT cdm_version FROM cdm_source").fetchall()
            if versions != [("v5.3.1",)]:
                raise CommandError("OMOP source must be CDM v5.3.1")
            vocabulary_versions = sorted(
                row[0]
                for row in source.execute(
                    "SELECT DISTINCT vocabulary_version FROM cdm_source WHERE vocabulary_version IS NOT NULL"
                ).fetchall()
            )
            schema = {table: columns_for(source, table) for table in TABLES}
            fingerprint = schema_fingerprint(schema)
            if options["dry_run"]:
                self.stdout.write(json.dumps({"tables": len(TABLES), "schema_sha256": fingerprint}))
                return

            db = settings.DATABASES["clinical"]
            connection = psycopg.connect(
                host=db["HOST"],
                port=db["PORT"],
                dbname=db["NAME"],
                user=os.environ.get("CLINICAL_IMPORT_DB_USER", db["USER"]),
                password=os.environ.get("CLINICAL_IMPORT_DB_PASSWORD", db["PASSWORD"]),
            )
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "CREATE TABLE IF NOT EXISTS import_metadata "
                        "(source_name text PRIMARY KEY, schema_sha256 text NOT NULL, "
                        "cdm_version text NOT NULL, vocabulary_versions jsonb NOT NULL, "
                        "imported_at timestamptz NOT NULL DEFAULT now())"
                    )
                    cursor.execute(
                        "SELECT schema_sha256 FROM import_metadata WHERE source_name = %s",
                        ("ehrshot_omop",),
                    )
                    previous = cursor.fetchone()
                    if previous and previous[0] != fingerprint:
                        raise CommandError("Clinical schema fingerprint differs from prior import")
                connection.commit()
                counts = {}
                for table in TABLES:
                    try:
                        counts[table] = import_table(
                            source, connection, table, schema[table], options["batch_size"]
                        )
                        connection.commit()
                    except Exception:
                        connection.rollback()
                        raise
                    self.stdout.write(f"{table}: {counts[table]}")
                with connection.cursor() as cursor:
                    for table, fields in INDEXES.items():
                        for field in fields:
                            cursor.execute(
                                sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} ({})").format(
                                    sql.Identifier(f"idx_{table}_{field}"),
                                    sql.Identifier(table),
                                    sql.Identifier(field),
                                )
                            )
                    for table, fields in PRIMARY_KEYS.items():
                        cursor.execute(
                            sql.SQL("CREATE UNIQUE INDEX IF NOT EXISTS {} ON {} ({})").format(
                                sql.Identifier(f"pk_{table}"),
                                sql.Identifier(table),
                                sql.SQL(", ").join(map(sql.Identifier, fields)),
                            )
                        )
                    for table in (
                        "person",
                        "concept",
                        "visit_occurrence",
                        "condition_occurrence",
                        "measurement",
                        "drug_exposure",
                    ):
                        cursor.execute(sql.SQL("ANALYZE {}").format(sql.Identifier(table)))
                    cursor.execute(
                        "INSERT INTO import_metadata "
                        "(source_name, schema_sha256, cdm_version, vocabulary_versions) "
                        "VALUES (%s, %s, %s, %s::jsonb) ON CONFLICT (source_name) DO NOTHING",
                        ("ehrshot_omop", fingerprint, "v5.3.1", json.dumps(vocabulary_versions)),
                    )
                connection.commit()
                self.stdout.write(
                    json.dumps({"schema_sha256": fingerprint, "rows": counts}, sort_keys=True)
                )
            finally:
                connection.close()
        finally:
            source.close()
