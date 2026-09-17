# OMOP CDM adapter

Django queries the PostgreSQL `clinical_db` copy of the EHRShot OMOP CDM v5.3.1
snapshot. The DuckDB file is an import source, not a live application database.
The web database role is read-only; import uses a separate role. Clinical
queries require a completed import metadata record that captures source and
vocabulary provenance.

| Cohort field | OMOP source |
| --- | --- |
| Patient | `person.person_id` |
| Sex | `person.gender_concept_id` through `concept`, with source fallback |
| Birth date | `person.birth_datetime`, with year/month/day fallback |
| Diagnosis | `condition_occurrence.condition_start_date` and concept/source values |
| Lab | `measurement.measurement_date`, `value_as_number`, and concept/source values |
| Drug | `drug_exposure.drug_exposure_start_date`, `quantity`, and concept/source values |
| Patient category | `visit_occurrence.visit_concept_id` through `concept` |

The query builder normalizes diagnosis, measurement, and drug events into a
common event stream, selects each patient's earliest matching index date T0,
then applies demographics and nested inclusion/exclusion predicates. Text and
numeric inputs are bound SQL parameters, not interpolated into the live query.
The builder supports code, name, group, event date, numeric/raw value,
patient category, age, and days from T0 filters.

The imported data can contain unmapped source concepts, missing units, and
incomplete visit linkage. Validate phenotype logic and data quality for each
research question rather than treating a matching count as clinical truth.
Never substitute identifiable data into tests or committed snapshots.
