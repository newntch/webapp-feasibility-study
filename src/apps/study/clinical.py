from django.db import connections

from .clinical_sql import build_count_query

REQUIRED_TABLES = (
    "person",
    "concept",
    "condition_occurrence",
    "measurement",
    "drug_exposure",
    "visit_occurrence",
    "cdm_source",
)


def ensure_clinical_ready():
    """Verify the PostgreSQL clinical database can serve OMOP feasibility queries."""
    with connections["clinical"].cursor() as cursor:
        cursor.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = current_schema() AND table_name = ANY(%s)",
            [list(REQUIRED_TABLES)],
        )
        found = {row[0] for row in cursor.fetchall()}
        missing = set(REQUIRED_TABLES) - found
        if missing:
            raise RuntimeError("Clinical database is missing required OMOP tables")
        cursor.execute("SELECT DISTINCT cdm_version FROM cdm_source")
        if cursor.fetchall() != [("v5.3.1",)]:
            raise RuntimeError("Clinical database must use OMOP CDM v5.3.1")


def run_feasibility(config):
    ensure_clinical_ready()
    query, params = build_count_query(config)
    with connections["clinical"].cursor() as cursor:
        cursor.execute(query, params)
        total, index, demographic, inclusion, final = map(int, cursor.fetchone())
    return {
        "totalPatients": total,
        "indexEligibleCount": index,
        "excludedCount": max(0, index - final),
        "finalCount": final,
        "included": [],
        "rows": [],
        "conceptSummary": {"diagnosis": [], "lab": [], "drug": []},
        "attrition": [
            {"label": "Has index event (T0)", "count": index},
            {
                "label": "After demographic filters",
                "count": demographic,
                "removed": max(0, index - demographic),
            },
            {
                "label": "After inclusion condition logic",
                "count": inclusion,
                "removed": max(0, demographic - inclusion),
            },
            {
                "label": "After exclusion condition logic",
                "count": final,
                "removed": max(0, inclusion - final),
            },
        ],
    }
