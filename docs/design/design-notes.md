# Design Notes

## Product Goal

Researchers need a fast way to estimate whether a clinical study is feasible before writing a full protocol or requesting production data extracts.

## Reference Patterns

- ATLAS/OHDSI: index event, cohort entry date, inclusion/exclusion criteria, and attrition-style result review.
- i2b2: panel-like criteria building across diagnosis, lab, and medication domains.
- OMOP CDM: all feasibility queries use the OMOP tables in `clinical_db`.

## Prototype Decisions

- Keep clinical data in PostgreSQL and use de-identified data for development.
- Keep cohort configuration and validation in browser modules; generate and run SQL in Django.
- Keep the first UI no-dependency and static so the feasibility workflow can be reviewed before choosing a full application stack.

## Next Backend Evolution

- Add vocabulary/concept mapping tables when the clinical dataset requires them.
- Add governance review workflow.
- Add small-cell suppression before showing counts from real patient data.
