"""OMOP v5.3.1 feasibility SQL for PostgreSQL.

Only fixed identifiers appear in SQL. Every value from a cohort configuration is bound.
"""

from datetime import date
from math import isfinite

EVENTS = {
    "diagnosis": (
        "condition_occurrence",
        "co",
        "condition_concept_id",
        "condition_start_date",
        "condition_source_value",
        "NULL::double precision",
    ),
    "lab": (
        "measurement",
        "me",
        "measurement_concept_id",
        "measurement_date",
        "measurement_source_value",
        "me.value_as_number::double precision",
    ),
    "drug": (
        "drug_exposure",
        "de",
        "drug_concept_id",
        "drug_exposure_start_date",
        "drug_source_value",
        "de.quantity::double precision",
    ),
}
FIELDS = {
    "domain": ("e.domain", "select"),
    "code": ("e.code", "text"),
    "name": ("e.name", "text"),
    "groupName": ("e.group_name", "text"),
    "eventDate": ("e.event_date", "date"),
    "numericValue": ("e.numeric_value", "number"),
    "rawValue": ("e.raw_value", "text"),
    "patientCategory": ("e.patient_category", "select"),
    "ageAtEvent": ("e.age_at_event", "number"),
    "daysFromT0": ("e.event_date - p.t0_date", "number"),
}
OPS = {
    "text": {
        "contains",
        "does_not_contain",
        "is",
        "is_not",
        "is_empty",
        "is_not_empty",
        "starts_with",
        "ends_with",
    },
    "number": {
        "is",
        "is_not",
        "greater_than",
        "less_than",
        "greater_than_or_equal",
        "less_than_or_equal",
        "between",
        "is_empty",
    },
    "date": {
        "exact_date",
        "before",
        "after",
        "on_or_before",
        "on_or_after",
        "between",
        "today",
        "this_month",
    },
    "select": {"is", "is_not", "is_any_of", "is_none_of", "is_empty"},
}


def number(value):
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError("Invalid numeric filter value") from None
    if not isfinite(result):
        raise ValueError("Invalid numeric filter value")
    return result


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("Invalid date filter value") from None


def condition_sql(node, params, allow_t0):
    field = node.get("field")
    if field not in FIELDS or (field == "daysFromT0" and not allow_t0):
        raise ValueError(f"Unsupported field: {field}")
    expression, kind = FIELDS[field]
    op = node.get("operator")
    if op not in OPS[kind]:
        raise ValueError(f"Unsupported operator for {field}: {op}")
    value = node.get("value")
    if kind in ("text", "select"):
        cast = f"LOWER(COALESCE({expression}::text, ''))"
        if op == "is_empty":
            return f"TRIM({cast}) = ''"
        if op == "is_not_empty":
            return f"TRIM({cast}) <> ''"
        if op in ("is_any_of", "is_none_of"):
            if not isinstance(value, list) or not value:
                raise ValueError("Selection list cannot be empty")
            params.extend(str(item) for item in value)
            placeholders = ", ".join("LOWER(%s)" for _ in value)
            negative = " NOT" if op == "is_none_of" else ""
            return f"{cast}{negative} IN ({placeholders})"
        if value is None or value == "":
            raise ValueError("Text filter value is required")
        params.append(str(value))
        return {
            "contains": f"STRPOS({cast}, LOWER(%s)) > 0",
            "does_not_contain": f"STRPOS({cast}, LOWER(%s)) = 0",
            "starts_with": f"STARTS_WITH({cast}, LOWER(%s))",
            "ends_with": f"ENDS_WITH({cast}, LOWER(%s))",
            "is": f"{cast} = LOWER(%s)",
            "is_not": f"{cast} <> LOWER(%s)",
        }[op]
    if kind == "number":
        if op == "is_empty":
            return f"{expression} IS NULL"
        if op == "between":
            if not isinstance(value, dict):
                raise ValueError("Number range is required")
            parts = []
            for key, symbol in (("from", ">="), ("to", "<=")):
                if value.get(key) not in (None, ""):
                    params.append(number(value[key]))
                    parts.append(f"{expression} {symbol} %s")
            if not parts:
                raise ValueError("Number range is empty")
            return "(" + " AND ".join(parts) + ")"
        params.append(number(value))
        symbol = {
            "is": "=",
            "is_not": "<>",
            "greater_than": ">",
            "less_than": "<",
            "greater_than_or_equal": ">=",
            "less_than_or_equal": "<=",
        }[op]
        return f"{expression} {symbol} %s"
    cast = f"{expression}::date"
    if op == "today":
        return f"{cast} = CURRENT_DATE"
    if op == "this_month":
        return f"DATE_TRUNC('month', {cast}) = DATE_TRUNC('month', CURRENT_DATE)"
    if op == "between":
        if not isinstance(value, dict):
            raise ValueError("Date range is required")
        parts = []
        for key, symbol in (("from", ">="), ("to", "<=")):
            if value.get(key):
                params.append(iso_date(value[key]))
                parts.append(f"{cast} {symbol} %s")
        if not parts:
            raise ValueError("Date range is empty")
        return "(" + " AND ".join(parts) + ")"
    params.append(iso_date(value))
    symbol = {
        "exact_date": "=",
        "before": "<",
        "after": ">",
        "on_or_before": "<=",
        "on_or_after": ">=",
    }[op]
    return f"{cast} {symbol} %s"


def group_sql(group, params, allow_t0):
    children = group.get("children", [])
    if not isinstance(children, list):
        raise ValueError("Filter children must be a list")
    if not children:
        raise ValueError("Filter group is empty")
    logic = group.get("logic", "AND")
    if logic not in ("AND", "OR"):
        raise ValueError("Filter logic must be AND or OR")
    parts = []
    for child in children:
        if child.get("type") == "group":
            parts.append(group_sql(child, params, allow_t0))
        elif child.get("type") == "condition":
            parts.append(condition_sql(child, params, allow_t0))
        else:
            raise ValueError("Unknown filter node")
    return "(" + f" {logic} ".join(parts) + ")"


def legacy_filter(rule, criteria):
    children = []

    def condition(field, operator, value):
        return {"type": "condition", "field": field, "operator": operator, "value": value}

    if rule.get("domain"):
        children.append(condition("domain", "is", rule["domain"]))
    concepts = [
        concept
        for concept in rule.get("concepts", [])
        if concept.get("code") or concept.get("name")
    ]
    if concepts:
        children.append(
            {
                "type": "group",
                "logic": "OR",
                "children": [
                    condition(
                        "code" if concept.get("code") else "name",
                        "is",
                        concept.get("code") or concept.get("name"),
                    )
                    for concept in concepts
                ],
            }
        )
    elif rule.get("query"):
        children.append(
            {
                "type": "group",
                "logic": "OR",
                "children": [
                    condition(field, "contains", rule["query"])
                    for field in ("code", "name", "groupName")
                ],
            }
        )
    operators = {
        ">": "greater_than",
        ">=": "greater_than_or_equal",
        "<": "less_than",
        "<=": "less_than_or_equal",
        "=": "is",
    }
    for value_key, op_key in (("labValue", "labOperator"), ("value", "operator")):
        if rule.get(value_key) not in (None, ""):
            children.append(
                condition("numericValue", operators.get(rule.get(op_key), "is"), rule[value_key])
            )
    if criteria and rule.get("timing") in ("before", "after", "within"):
        before = rule.get("daysBefore")
        after = rule.get("daysAfter")
        lower = -abs(number(before)) if before not in (None, "") else ""
        upper = after if after not in (None, "") else 0
        if rule["timing"] == "before":
            value = {"from": lower, "to": 0}
        elif rule["timing"] == "after":
            value = {"from": 0, "to": upper}
        else:
            value = {"from": lower, "to": upper}
        children.append(condition("daysFromT0", "between", value))
    return {"type": "group", "logic": "AND", "children": children}


def active_rules(config, key):
    rules = config.get(key) or (
        [config["indexEvent"]] if key == "indexEvents" and config.get("indexEvent") else []
    )
    if not isinstance(rules, list):
        raise ValueError(f"{key} must be a list")
    normalized = []
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError(f"{key} rules must be objects")
        filt = rule.get("filter") or legacy_filter(rule, key != "indexEvents")
        if filt.get("children"):
            normalized.append({**rule, "filter": filt})
    return normalized


def person_cte():
    return """person_base AS (
 SELECT p.person_id,
 COALESCE(p.birth_datetime::date,
   CASE WHEN p.year_of_birth IS NOT NULL AND p.month_of_birth IS NOT NULL
        AND p.day_of_birth IS NOT NULL
   THEN make_date(p.year_of_birth::integer, p.month_of_birth::integer, p.day_of_birth::integer)
   END) AS birth_date,
 COALESCE(NULLIF(gc.concept_name, 'No matching concept'),
          NULLIF(p.gender_source_value, ''), '') AS gender
 FROM person p LEFT JOIN concept gc ON gc.concept_id = p.gender_concept_id
)"""


def events_cte():
    parts = []
    for domain, (table, alias, concept_id, event_date, source_value, numeric) in EVENTS.items():
        source = f"{alias}.{source_value}::text"
        concept_valid = "c.concept_id IS NULL OR c.concept_id = 0 OR LOWER(COALESCE(c.concept_name, '')) = 'no matching concept'"
        code = f"CASE WHEN {concept_valid} THEN COALESCE(NULLIF({source}, ''), '') ELSE COALESCE(NULLIF(c.concept_code, ''), NULLIF({source}, ''), '') END"
        name = f"CASE WHEN {concept_valid} THEN COALESCE(NULLIF({source}, ''), '') ELSE COALESCE(NULLIF(c.concept_name, ''), NULLIF({source}, ''), '') END"
        visit_name = "LOWER(COALESCE(vc.concept_name, ''))"
        category = f"CASE WHEN {visit_name} LIKE '%%emergency%%' THEN 'ED' WHEN {visit_name} LIKE '%%inpatient%%' THEN 'IPD' WHEN {visit_name} LIKE '%%outpatient%%' OR {visit_name} LIKE '%%office visit%%' THEN 'OPD' ELSE COALESCE(vc.concept_name, '') END"
        event = f"{alias}.{event_date}::date"
        age = f"(EXTRACT(YEAR FROM {event}) - EXTRACT(YEAR FROM pb.birth_date))::double precision"
        parts.append(f"""SELECT {alias}.person_id, '{domain}' AS domain, {event} AS event_date,
 {code} AS code, {name} AS name, COALESCE(c.concept_class_id, '') AS group_name,
 {numeric} AS numeric_value, COALESCE(NULLIF({source}, ''), '') AS raw_value,
 {category} AS patient_category, {age} AS age_at_event
 FROM {table} {alias} JOIN person_base pb ON pb.person_id = {alias}.person_id
 LEFT JOIN concept c ON c.concept_id = {alias}.{concept_id}
 LEFT JOIN visit_occurrence v ON v.visit_occurrence_id = {alias}.visit_occurrence_id
 LEFT JOIN concept vc ON vc.concept_id = v.visit_concept_id
 WHERE {alias}.{event_date} IS NOT NULL""")
    return "all_events AS NOT MATERIALIZED (" + " UNION ALL ".join(parts) + ")"


def joined_exists(rules, params, negate=False):
    pieces = []
    for index, rule in enumerate(rules):
        joiner = rule.get("joiner", "AND").upper()
        if joiner not in ("AND", "OR"):
            raise ValueError("Rule joiner must be AND or OR")
        if index:
            pieces.append(joiner)
        predicate = group_sql(rule["filter"], params, True)
        pieces.append(
            f"EXISTS (SELECT 1 FROM all_events e WHERE e.person_id = p.person_id AND {predicate})"
        )
    expression = "(" + " ".join(pieces) + ")"
    return f"NOT {expression}" if negate else expression


def build_count_query(config):
    if not isinstance(config, dict):
        raise ValueError("Cohort config must be an object")
    params = []
    ctes = [person_cte()]
    indexes = active_rules(config, "indexEvents")
    includes = active_rules(config, "inclusionCriteria")
    excludes = active_rules(config, "exclusionCriteria")
    if indexes or includes or excludes:
        ctes.append(events_cte())
    if indexes:
        window = config.get("indexWindow") or {}
        for i, rule in enumerate(indexes):
            predicate = group_sql(rule["filter"], params, False)
            dates = []
            for key, symbol in (("from", ">="), ("to", "<=")):
                value = window.get(key) or window.get("start" if key == "from" else "end")
                if value:
                    params.append(iso_date(value))
                    dates.append(f"e.event_date {symbol} %s")
            where = " AND ".join([predicate, *dates])
            ctes.append(
                f"IndexRule{i} AS (SELECT DISTINCT e.person_id, e.event_date FROM all_events e WHERE {where})"
            )
        union = " UNION ALL ".join(
            f"SELECT person_id, event_date FROM IndexRule{i}" for i in range(len(indexes))
        )
        checks = []
        for i, rule in enumerate(indexes):
            joiner = rule.get("joiner", "AND").upper()
            if joiner not in ("AND", "OR"):
                raise ValueError("Index joiner must be AND or OR")
            if i:
                checks.append(joiner)
            checks.append(f"EXISTS (SELECT 1 FROM IndexRule{i} x WHERE x.person_id = p.person_id)")
        ctes.append(
            f"IndexCohort AS (SELECT p.person_id, MIN(i.event_date) AS t0_date FROM person_base p JOIN ({union}) i ON i.person_id = p.person_id WHERE {' '.join(checks)} GROUP BY p.person_id)"
        )
    demo = config.get("demographics") or {}
    age_date = "i.t0_date" if indexes else "CURRENT_DATE"
    age = f"(EXTRACT(YEAR FROM {age_date}) - EXTRACT(YEAR FROM p.birth_date))"
    predicates = []
    for field, symbol in (("minAge", ">="), ("maxAge", "<=")):
        value = demo.get(field, demo.get("ageMin" if field == "minAge" else "ageMax"))
        if value not in (None, ""):
            params.append(number(value))
            predicates.append(f"{age} {symbol} %s")
    if demo.get("sex") and demo["sex"] != "Any":
        params.append(str(demo["sex"]))
        predicates.append("LOWER(COALESCE(p.gender, '')) = LOWER(%s)")
    join = "JOIN IndexCohort i ON i.person_id = p.person_id" if indexes else ""
    t0 = "i.t0_date" if indexes else "NULL::date"
    where = "WHERE " + " AND ".join(predicates) if predicates else ""
    ctes.append(
        f"BasePatients AS (SELECT p.person_id, p.birth_date, p.gender, {t0} AS t0_date FROM person_base p {join} {where})"
    )
    if not indexes:
        return (
            "WITH "
            + ", ".join(ctes)
            + " SELECT (SELECT COUNT(*) FROM person_base) AS totalPatients, 0::bigint AS indexEligibleCount, 0::bigint AS demographicCount, 0::bigint AS inclusionCount, 0::bigint AS finalCount",
            params,
        )
    inclusion_values = []
    exclusion_values = []
    inclusion_sql = joined_exists(includes, inclusion_values) if includes else "TRUE"
    ctes.append(
        f"InclusionPatients AS MATERIALIZED (SELECT p.* FROM BasePatients p WHERE {inclusion_sql})"
    )
    final_sql = joined_exists(excludes, exclusion_values, negate=True) if excludes else "TRUE"
    params.extend(inclusion_values)
    params.extend(exclusion_values)
    query = (
        "WITH "
        + ", ".join(ctes)
        + " SELECT (SELECT COUNT(*) FROM person_base) AS totalPatients,"
        + " (SELECT COUNT(*) FROM IndexCohort) AS indexEligibleCount,"
        + " (SELECT COUNT(*) FROM BasePatients) AS demographicCount,"
        + " (SELECT COUNT(*) FROM InclusionPatients) AS inclusionCount,"
        + f" (SELECT COUNT(*) FROM InclusionPatients p WHERE {final_sql}) AS finalCount"
    )
    return query, params
