# Product and usage

The cohort builder combines an index event (T0), demographic filters, and
nested inclusion/exclusion rules for diagnosis, lab, and drug OMOP domains.
Negative `Days from T0` values mean before T0; positive values mean after.
No concepts are selected at startup. Presets provide examples only.

The dictionary page searches code, name, group, and count in the checked-in
`public/data/master-dictionary.json` snapshot. To refresh the public source
sheets on a development machine, run:

```bash
uv run python manage.py sync_dictionary
```

Review the generated snapshot diff and rebuild the web image before deploying
it. A failed fetch leaves the previous snapshot untouched. The source-sheet
links remain visible in the dictionary page.

Signed-in users can save cohort definitions and inspect their own run and
session audit logs. These records are stored in `application_db`. Clinical
counts use `clinical_db`; the web role cannot modify that database. The SQL
preview displays PostgreSQL SQL with placeholders, while live execution binds
the selected values separately. Review any phenotype and mapping assumptions
before research use.

The workflow diagram shows index, demographic, inclusion, exclusion, and final
counts. It can be exported as SVG or PNG. The browser-facing JavaScript is
served as plain modules by Django; it does not require a build toolchain.
