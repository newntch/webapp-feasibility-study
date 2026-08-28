# OMOP CDM adapter

The feasibility builder keeps its existing cohort configuration contract and
translates it into DuckDB SQL over OMOP CDM tables. Select the adapter with
`clinicalDataSource: "omop-duckdb"` and set `omopDuckdb.path` to the database
file.

## Field mapping

| Cohort field | OMOP source |
| --- | --- |
| patient | `person.person_id` |
| sex | `person.gender_concept_id` -> `concept.concept_name`, with `gender_source_value` fallback |
| birth date | `person.birth_datetime`, with year/month/day fallback |
| diagnosis event | `condition_occurrence.condition_start_date`, `condition_concept_id`, `condition_source_value` |
| lab event | `measurement.measurement_date`, `measurement_concept_id`, `value_as_number`, `measurement_source_value` |
| drug event | `drug_exposure.drug_exposure_start_date`, `drug_concept_id`, `quantity`, `drug_source_value` |
| code/name | standard `concept_code`/`concept_name`; source values are used for concept ID `0` or unmapped events |
| group name | `concept.concept_class_id` |
| patient category | `visit_occurrence.visit_concept_id` -> `concept.concept_name`, normalized to OPD/IPD/ED where recognizable |

The three event tables are normalized into an `AllEvents` CTE with a common
shape. `IndexRuleN` CTEs find each configured index rule, `IndexCohort` assigns
the earliest matching event as T0, and `BasePatients` applies demographics at
T0. Inclusion and exclusion panels are correlated `EXISTS`/`NOT EXISTS`
predicates against `AllEvents`.

## Example configuration

```json
{
  "clinicalDataSource": "omop-duckdb",
  "omopDuckdb": {
    "path": "data/omop/ehrshot_omop/ehrshot_omop.duckdb"
  }
}
```

The query builder supports the existing `domain`, `code`, `name`,
`groupName`, `eventDate`, `numericValue`, `rawValue`, `patientCategory`,
`ageAtEvent`, and `daysFromT0` fields. Numeric measurements use
`measurement.value_as_number`; drug quantity uses `drug_exposure.quantity`.
Date arithmetic uses DuckDB `DATE_DIFF`, and all user text is SQL-escaped by
the builder.

## Local validation

The adapter was tested against the supplied EHRShot OMOP DuckDB file. The
database contains `person` rows and clinical events in the three OMOP domains;
the live count query and concept catalog query both execute through
`@duckdb/node-api`. The source file is treated as synthetic/de-identified
research data. Do not substitute identifiable clinical data in this project.
