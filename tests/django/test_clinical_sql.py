"""PostgreSQL OMOP query contract, using synthetic cohort rules only."""

import unittest

from apps.study.clinical_sql import build_count_query


def condition(field, operator, value):
    return {"type": "condition", "field": field, "operator": operator, "value": value}


def group(logic, *children):
    return {"type": "group", "logic": logic, "children": list(children)}


def rule(filter_group, joiner="AND"):
    return {"joiner": joiner, "filter": filter_group}


def bound_values(params):
    return list(params.values()) if isinstance(params, dict) else list(params)


def contains_number(params, expected):
    for value in bound_values(params):
        try:
            if float(value) == expected:
                return True
        except (TypeError, ValueError):
            continue
    return False


class ClinicalSqlTests(unittest.TestCase):
    def test_nested_conditions_preserve_grouping_and_count_stages(self):
        config = {
            "indexEvents": [
                rule(
                    group(
                        "AND",
                        condition("domain", "is", "diagnosis"),
                        group(
                            "OR",
                            condition("code", "is", "59621000"),
                            condition("code", "is", "55822004"),
                        ),
                    )
                )
            ],
            "inclusionCriteria": [
                rule(
                    group(
                        "AND",
                        condition("domain", "is", "lab"),
                        condition("numericValue", "greater_than_or_equal", "7"),
                    )
                )
            ],
            "exclusionCriteria": [rule(group("AND", condition("domain", "is", "drug")))],
        }

        sql, params = build_count_query(config)

        self.assertRegex(sql, r"(?i)\bFROM\s+condition_occurrence\b")
        self.assertRegex(sql, r"(?i)\bFROM\s+measurement\b")
        self.assertRegex(sql, r"(?i)\bFROM\s+drug_exposure\b")
        self.assertRegex(sql, r"(?is)\bIndexCohort\b.*\bBasePatients\b")
        self.assertRegex(sql, r"(?is)\bAND\s*\(.*\bOR\b.*\)")
        for stage in (
            "totalPatients",
            "indexEligibleCount",
            "demographicCount",
            "inclusionCount",
            "finalCount",
        ):
            self.assertIn(stage, sql)
        values = [str(value) for value in bound_values(params)]
        for expected in ("diagnosis", "59621000", "55822004", "lab", "drug"):
            self.assertIn(expected, values)
        self.assertTrue(contains_number(params, 7))

    def test_user_values_are_bound_instead_of_interpolated(self):
        hostile = "O'Brien'; DROP TABLE person; --"
        sql, params = build_count_query(
            {
                "indexEvents": [rule(group("AND", condition("name", "contains", hostile)))],
                "indexWindow": {"from": "2020-01-01", "to": "2023-12-31"},
                "demographics": {"sex": "Female"},
            }
        )

        self.assertNotIn(hostile, sql)
        self.assertNotIn("DROP TABLE", sql)
        self.assertIn("%s", sql)
        values = [str(value) for value in bound_values(params)]
        self.assertTrue(any(hostile in value for value in values))
        self.assertTrue(any("2020-01-01" in value for value in values))
        self.assertTrue(any("2023-12-31" in value for value in values))
        self.assertTrue(any("Female" in value for value in values))

    def test_relative_days_and_age_use_postgresql_expressions(self):
        sql, params = build_count_query(
            {
                "indexEvents": [rule(group("AND", condition("code", "is", "synthetic-code")))],
                "demographics": {"minAge": 18},
                "inclusionCriteria": [
                    rule(
                        group("AND", condition("daysFromT0", "between", {"from": "0", "to": "30"}))
                    )
                ],
            }
        )

        self.assertNotIn("DATE_DIFF", sql.upper())
        self.assertNotIn("DATEDIFF", sql.upper())
        self.assertNotIn("TRY_CAST", sql.upper())
        self.assertRegex(sql, r"(?i)\bT0_DATE\b")
        self.assertRegex(sql, r"(?i)\bEVENT_DATE\b")
        self.assertRegex(sql, r"(?i)\bBIRTH_DATE\b")
        self.assertTrue(contains_number(params, 30))

    def test_invalid_field_and_operator_fail_before_query_execution(self):
        invalid_rules = (
            condition("person_id; DROP TABLE person", "is", "1"),
            condition("code", "raw_sql", "1"),
            condition("daysFromT0", "is", "0"),
        )
        for invalid in invalid_rules:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                build_count_query({"indexEvents": [rule(group("AND", invalid))]})

    def test_empty_index_has_total_and_zero_downstream_counts(self):
        sql, params = build_count_query({})

        self.assertRegex(sql, r"(?i)\bperson\b")
        self.assertRegex(sql, r"(?i)\btotalPatients\b")
        for stage in ("indexEligibleCount", "demographicCount", "inclusionCount", "finalCount"):
            self.assertRegex(sql, rf"(?is)(?:\b0\b|CAST\s*\(\s*0\b).*\b{stage}\b")
        self.assertEqual(bound_values(params), [])
