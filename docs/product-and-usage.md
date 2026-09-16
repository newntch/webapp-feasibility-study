# Product and usage

The prototype follows ATLAS/OHDSI-style index events and cohort entry dates,
combines them with i2b2-style inclusion and exclusion panels, and provides an
Airtable-style nested condition builder.

## Current scope

- Domains: diagnosis, lab, and drug release or prescription.
- Cohort logic: reusable Airtable-style nested filter groups for T0 index
  conditions, inclusion criteria, and exclusion criteria.
- Filter groups: nested AND/OR groups, add/delete condition rows, add/delete
  groups, typed operators by field type, and validation against the allowed
  field whitelist.
- Timing: inclusion and exclusion timing uses `Days from T0`; negative values
  mean before T0 and positive values mean after T0.
- Startup: no concepts are selected initially; preset buttons load example
  cohort definitions.
- Data: synthetic only. Local development reads
  `public/data/synthetic-clinical-data.json` first, then the committed example
  file `public/data/synthetic-clinical-data_example.json`.

## Master dictionary

Open <http://localhost:4173/dictionary.html> to search the diagnosis, lab, and
drug master dictionary before building conditions.

- Search supports code, name, group, and count.
- Domain tabs focus on diagnosis, lab, or drug entries.
- Each result provides copy actions for code and name.
- The page reads `public/data/master-dictionary.json`.
- Source links for the ICD-10, ICD-9, lab, and drug sheets appear in the UI.

Refresh the local snapshot from the configured Google Sheets with:

```bash
pnpm sync-dictionary
```

## Saved cohorts

Use **Save current** to store the research question, T0 conditions,
demographics, inclusion rules, exclusion rules, nested group logic, timing
windows, and lab value filters.

Saved definitions can be searched by name or content, reloaded, and deleted.
They are handled through backend APIs and stored by the active application
storage mode:

- Local mode writes to `data/saved-cohorts.json` on the server.
- SQL Server mode writes to the configured SQL Server application tables.

## Session and run logs

Open <http://localhost:4173/logs.html> to view prototype audit logs.

- Each signed-in session receives a generated session record.
- Each **Run feasibility count** action creates a run log.
- The signed-in login identity is included in feasibility run audit records.
- Run logs include the research question, T0 count, final cohort count,
  attrition, generated SQL, full cohort config, and selected filter-tree
  conditions.
- Logs can be searched and exported as JSON.

The page reads the active backend storage mode. Local mode stays on the server;
SQL mode uses the shared SQL database.

## Generated SQL

The SQL Builder panel creates SQL Server-style cohort SQL from the selected
criteria and provides a Copy SQL button.

- Base table: `Patient_Info`
- Patient key: `OH_PID`
- Diagnosis table: `Diagnosis`
- Laboratory table: `Laboratory`
- Medication table: `Medication`
- SQL pattern: CTEs with `EXISTS` / `NOT EXISTS`
- Date functions: `DATEDIFF`, `DATEADD`, and `BETWEEN`
- Date format: `'YYYY-MM-DD'`

The generated SQL is a feasibility-study draft, not a production query.
Review table and column mappings before running it against a real clinical
database.

## Workflow diagram

The cohort workflow diagram shows five attrition steps:

1. Has index event (T0)
2. After demographic filters
3. After inclusion logic
4. After exclusion logic
5. Final cohort

Blue means no patient drop, amber means patients were excluded at that step,
and teal/green marks the final cohort. The diagram can be downloaded as SVG or
2x PNG. Clicking a node sends a follow-up prompt through `sendPrompt()` when
the hosting environment provides it.

## Data assumptions

- `hn` is the central synthetic patient key.
- Diagnosis T0 uses `diagnosis_record.service_date`.
- Lab T0 uses `lab_result.test_date` and parses numeric values from
  `result_value`.
- Drug release uses `prescription_order.order_date`.
- When multiple T0 conditions are configured, each condition can be combined
  with AND/OR. The first matching T0 condition by list order sets the cohort
  entry date for before/after timing.
- Age at T0 is derived from diagnosis or lab event age fields because
  `patient_master` does not contain birth date.

For source schema details, see the [data dictionary](references/data-dictionary.md).
