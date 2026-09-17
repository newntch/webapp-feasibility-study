from functools import lru_cache

from django.db import connections

from .clinical_sql import build_count_query

CATALOG_SQL = """
WITH used_concepts AS (
 SELECT 'diagnosis' AS domain, condition_concept_id AS concept_id, COUNT(*) AS event_count
 FROM condition_occurrence WHERE condition_concept_id IS NOT NULL AND condition_concept_id <> 0
 GROUP BY condition_concept_id
 UNION ALL
 SELECT 'lab', measurement_concept_id, COUNT(*)
 FROM measurement WHERE measurement_concept_id IS NOT NULL AND measurement_concept_id <> 0
 GROUP BY measurement_concept_id
 UNION ALL
 SELECT 'drug', drug_concept_id, COUNT(*)
 FROM drug_exposure WHERE drug_concept_id IS NOT NULL AND drug_concept_id <> 0
 GROUP BY drug_concept_id
)
SELECT uc.domain, c.concept_code, c.concept_name, COALESCE(c.concept_class_id, ''),
       SUM(uc.event_count)
FROM used_concepts uc JOIN concept c ON c.concept_id = uc.concept_id
WHERE c.concept_code IS NOT NULL AND c.concept_name IS NOT NULL
GROUP BY uc.domain, c.concept_code, c.concept_name, c.concept_class_id
ORDER BY uc.domain, c.concept_code, c.concept_name
"""


def ensure_import_ready():
    with connections["clinical"].cursor() as cursor:
        cursor.execute("SELECT 1 FROM import_metadata WHERE source_name = %s", ["ehrshot_omop"])
        if cursor.fetchone() is None:
            raise RuntimeError("Clinical import has not completed")


@lru_cache(maxsize=1)
def concept_catalog():
    ensure_import_ready()
    result = {"diagnosis": [], "lab": [], "drug": []}
    with connections["clinical"].cursor() as cursor:
        cursor.execute(CATALOG_SQL)
        for domain, code, name, group_name, count in cursor.fetchall():
            result[domain].append(
                {"code": code, "name": name, "groupName": group_name, "count": int(count)}
            )
    return result


def run_feasibility(config):
    ensure_import_ready()
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
