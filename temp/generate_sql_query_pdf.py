from pathlib import Path


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
LEFT = 52
RIGHT = 52
TOP = 790
BOTTOM = 48
BODY_WIDTH = 91
CODE_WIDTH = 103


def wrap_text(text, width):
    lines = []
    for original in text.splitlines():
        line = original
        if not line:
            lines.append("")
            continue
        while len(line) > width:
            cut = line.rfind(" ", 0, width + 1)
            if cut <= 0:
                cut = width
            lines.append(line[:cut])
            line = line[cut:].lstrip()
        lines.append(line)
    return lines


def escape_pdf_text(value):
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def text_command(font, size, x, y, value):
    return f"BT /{font} {size} Tf 1 0 0 1 {x:.1f} {y:.1f} Tm ({escape_pdf_text(value)}) Tj ET\n"


def add_text_page(pages, commands, page_number):
    commands.append(text_command("F1", 8, LEFT, 27, "Cohort Lens - SQL Query Explanation"))
    page_label = f"Page {page_number}"
    commands.append(text_command("F1", 8, PAGE_WIDTH - RIGHT - 34, 27, page_label))
    pages.append("".join(commands))


def build_pages():
    pages = []
    commands = []
    y = TOP
    page_number = 1

    def new_page():
        nonlocal commands, y, page_number
        add_text_page(pages, commands, page_number)
        page_number += 1
        commands = []
        y = TOP

    def ensure_space(height):
        nonlocal y
        if y - height < BOTTOM:
            new_page()

    def add_line(font, size, leading, line, x=LEFT):
        nonlocal y
        ensure_space(leading)
        commands.append(text_command(font, size, x, y, line))
        y -= leading

    def add_spacer(amount=7):
        nonlocal y
        ensure_space(amount)
        y -= amount

    add_line("F2", 19, 25, "Cohort Lens: SQL Query Explanation")
    add_line("F1", 10, 17, "Diagnosis Feasibility Study Webapp")
    add_spacer(7)
    add_line("F1", 10, 13, "This document explains the SQL generated and used by the Cohort Lens")
    add_line("F1", 10, 13, "clinical cohort feasibility prototype. The query is generated dynamically")
    add_line("F1", 10, 13, "from the cohort definition entered in the browser.")
    add_spacer(12)

    sections = [
        ("heading", "1. Overview"),
        ("paragraph", "The project does not use one fixed SQL query for cohort searches. The browser creates a cohort configuration, and src/sqlBuilder.js converts it into SQL Server syntax. When SQL Server mode is enabled, the SQL Server repository sends the generated query to SQL Server. In JSON mode, equivalent logic runs in JavaScript through src/cohortEngine.js."),
        ("paragraph", "The browser also displays the generated SQL as a preview. SQL Server feasibility execution uses the count query, which returns one row of staged counts rather than patient-level rows."),
        ("heading", "2. Clinical Table Mapping"),
        ("code", "Domain          Table          Event date       Code\nDiagnosis       Diagnosis      VISIT_DATE       ICD_CODE\nLaboratory      Laboratory      RESULT_DATE      LAB_CODE\nMedication      Medication      ORDER_DATE       DRUG_CODE"),
        ("paragraph", "The starter schema is in tests/sql-initial-setup.sql. The clinical tables are linked to Patient_Info through OH_PID."),
        ("heading", "3. Main Query Structure"),
        ("paragraph", "The generated query uses common table expressions (CTEs). Each CTE represents one logical stage of cohort construction."),
        ("subheading", "3.1 AllEvents"),
        ("paragraph", "AllEvents normalizes diagnosis, laboratory, and medication records into one event stream. It gives each event common fields such as patient ID, domain, event date, code, name, numeric value, patient category, and age at event."),
        ("code", "WITH AllEvents AS (\n  SELECT OH_PID, 'diagnosis' AS DOMAIN, VISIT_DATE AS EVENT_DATE,\n         ICD_CODE AS CODE, DISEASE_NAME AS NAME\n  FROM Diagnosis\n\n  UNION ALL\n\n  SELECT OH_PID, 'lab', RESULT_DATE, LAB_CODE, LAB_NAME\n  FROM Laboratory\n\n  UNION ALL\n\n  SELECT OH_PID, 'drug', ORDER_DATE, DRUG_CODE, DRUG_NAME\n  FROM Medication\n)"),
        ("subheading", "3.2 IndexRule CTEs"),
        ("paragraph", "Each T0/index rule becomes an IndexRule CTE. The CTE selects distinct patients and event dates that match the nested condition tree and the absolute T0 date window."),
        ("paragraph", "For the diabetes example, the logic is equivalent to:"),
        ("code", "IndexRule1 AS (\n  SELECT DISTINCT OH_PID, EVENT_DATE\n  FROM AllEvents\n  WHERE DOMAIN = 'diagnosis'\n    AND (CODE = 'E11.9' OR CODE = 'E11.65' OR CODE = 'E11.22')\n    AND EVENT_DATE BETWEEN '2023-01-01' AND '2025-12-31'\n)"),
        ("subheading", "3.3 IndexCohort"),
        ("paragraph", "IndexCohort joins matching events to Patient_Info and assigns a T0 date to each eligible patient. The current implementation uses the minimum matching event date as T0_DATE."),
        ("code", "IndexCohort AS (\n  SELECT p.OH_PID, MIN(i.EVENT_DATE) AS T0_DATE\n  FROM Patient_Info p\n  JOIN IndexRule1 i ON i.OH_PID = p.OH_PID\n  GROUP BY p.OH_PID\n)"),
        ("paragraph", "If there are multiple index rules, the query adds EXISTS checks for each rule and combines them with the configured AND or OR joiners."),
        ("subheading", "3.4 BasePatients"),
        ("paragraph", "BasePatients applies demographic criteria to the index cohort. It retains the patient columns and the calculated T0 date."),
        ("code", "BasePatients AS (\n  SELECT p.*, i.T0_DATE\n  FROM Patient_Info p\n  JOIN IndexCohort i ON i.OH_PID = p.OH_PID\n  WHERE DATEDIFF(YEAR, p.BIRTH_DATE, GETDATE()) >= 18\n)"),
        ("paragraph", "The supported demographic filters are minimum age, maximum age, and sex."),
        ("subheading", "3.5 Inclusion Criteria"),
        ("paragraph", "Each inclusion rule becomes a correlated EXISTS subquery. The event must belong to the current patient, match the rule, and satisfy any timing window relative to T0_DATE."),
        ("paragraph", "For example, the diabetes preset requires an HbA1c result within 180 days and metformin within 90 days after T0:"),
        ("code", "EXISTS (\n  SELECT 1 FROM AllEvents e\n  WHERE e.OH_PID = p.OH_PID\n    AND e.DOMAIN = 'lab'\n    AND e.CODE = 'HBA1C'\n    AND DATEDIFF(DAY, p.T0_DATE, e.EVENT_DATE) BETWEEN 0 AND 180\n)\nAND EXISTS (\n  SELECT 1 FROM AllEvents e\n  WHERE e.OH_PID = p.OH_PID\n    AND e.DOMAIN = 'drug'\n    AND e.CODE = 'MET500'\n    AND DATEDIFF(DAY, p.T0_DATE, e.EVENT_DATE) BETWEEN 0 AND 90\n)"),
        ("subheading", "3.6 Exclusion Criteria"),
        ("paragraph", "Exclusion rules are also EXISTS subqueries, but the combined expression is negated. Therefore, a patient is removed when any configured exclusion event is found by default."),
        ("code", "AND NOT EXISTS (\n  SELECT 1 FROM AllEvents e\n  WHERE e.OH_PID = p.OH_PID\n    AND e.DOMAIN = 'diagnosis'\n    AND e.CODE = 'N18.3'\n    AND DATEDIFF(DAY, p.T0_DATE, e.EVENT_DATE) BETWEEN -365 AND 0\n)"),
        ("heading", "4. Feasibility Count Query"),
        ("paragraph", "SQL Server mode wraps the CTEs in a single SELECT that produces staged attrition counts:"),
        ("code", "SELECT\n  (SELECT COUNT(*) FROM Patient_Info) AS totalPatients,\n  (SELECT COUNT(*) FROM IndexCohort) AS indexEligibleCount,\n  (SELECT COUNT(*) FROM BasePatients) AS demographicCount,\n  (...) AS inclusionCount,\n  (...) AS finalCount"),
        ("paragraph", "The values mean:"),
        ("bullet", "totalPatients: all rows in Patient_Info."),
        ("bullet", "indexEligibleCount: patients with at least one matching T0 event."),
        ("bullet", "demographicCount: T0 patients remaining after age and sex filters."),
        ("bullet", "inclusionCount: demographic patients satisfying all inclusion logic."),
        ("bullet", "finalCount: patients remaining after inclusion and exclusion logic."),
        ("heading", "5. Operator Translation"),
        ("paragraph", "The condition builder translates filter types into SQL expressions:"),
        ("bullet", "Text: equality, inequality, LIKE, starts-with, ends-with, and empty checks."),
        ("bullet", "Numbers: equality, comparisons, ranges, and NULL checks."),
        ("bullet", "Dates: exact date, before/after, ranges, today, and this month."),
        ("bullet", "Select fields: equality, IN, NOT IN, and empty checks."),
        ("bullet", "Days from T0: DATEDIFF(DAY, p.T0_DATE, e.EVENT_DATE)."),
        ("paragraph", "Text values are quoted and apostrophes are escaped. Numeric values are converted before being inserted into the SQL string. The query builder is still a draft string generator rather than a parameterized production query."),
        ("heading", "6. Other SQL Queries"),
        ("paragraph", "The project has additional SQL outside the cohort count query:"),
        ("bullet", "Dictionary bootstrap queries aggregate code, name, group, and occurrence counts from Diagnosis, Laboratory, and Medication."),
        ("bullet", "SQL Server app-storage queries manage users, sessions, OTPs, saved cohorts, audit sessions, and feasibility run logs."),
        ("bullet", "tests/sql-initial-setup.sql creates the clinical and application tables plus indexes intended to support these queries."),
        ("heading", "7. Important Limitations"),
        ("bullet", "The generated SQL is a feasibility-study draft and should be reviewed before use against real clinical data."),
        ("bullet", "SQL mode returns counts and attrition, not patient-level result rows."),
        ("bullet", "Age uses GETDATE() and BIRTH_DATE rather than an exact age-at-T0 calculation."),
        ("bullet", "When multiple T0 rules are matched, T0_DATE is currently the minimum matching event date."),
        ("bullet", "The query targets the project's local guide schema, not OMOP CDM tables."),
        ("paragraph", "Primary implementation files: src/sqlBuilder.js (SQL generation), src/server/sqlServerFeasibilityRepository.js (SQL Server execution), src/cohortEngine.js (equivalent JSON evaluation), and tests/sql-initial-setup.sql (starter SQL schema)."),
    ]

    for kind, value in sections:
        if kind == "heading":
            add_spacer(8)
            add_line("F2", 14, 19, value)
            add_spacer(3)
        elif kind == "subheading":
            add_spacer(5)
            add_line("F2", 11, 15, value)
            add_spacer(2)
        elif kind == "paragraph":
            for line in wrap_text(value, BODY_WIDTH):
                add_line("F1", 10, 13, line)
            add_spacer(5)
        elif kind == "code":
            add_spacer(3)
            for line in wrap_text(value, CODE_WIDTH):
                add_line("F3", 8.2, 10.5, line, LEFT + 8)
            add_spacer(6)
        elif kind == "bullet":
            bullet_lines = wrap_text(value, BODY_WIDTH - 4)
            for index, line in enumerate(bullet_lines):
                prefix = "- " if index == 0 else "  "
                add_line("F1", 10, 13, prefix + line, LEFT + 5)
            add_spacer(2)

    if commands:
        add_text_page(pages, commands, page_number)
    return pages


def make_pdf(output_path):
    pages = build_pages()
    objects = [None]

    def add_object(value):
        objects.append(value)
        return len(objects) - 1

    catalog_id = add_object("<< /Type /Catalog /Pages 2 0 R >>")
    pages_id = add_object(None)
    regular_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    bold_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    mono_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>")

    page_ids = []
    for stream in pages:
        stream_bytes = stream.encode("latin-1")
        content_id = add_object(f"<< /Length {len(stream_bytes)} >>\nstream\n{stream}endstream")
        page_id = add_object(
            "<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {regular_id} 0 R /F2 {bold_id} 0 R /F3 {mono_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        )
        page_ids.append(page_id)

    objects[pages_id] = f"<< /Type /Pages /Kids [{' '.join(f'{pid} 0 R' for pid in page_ids)}] /Count {len(page_ids)} >>"

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id in range(1, len(objects)):
        offsets.append(len(output))
        payload = objects[object_id].encode("latin-1")
        output.extend(f"{object_id} 0 obj\n".encode("ascii"))
        output.extend(payload)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects)}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects)} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )

    Path(output_path).write_bytes(output)
    print(f"Wrote {output_path} ({len(output)} bytes, {len(pages)} pages)")


if __name__ == "__main__":
    make_pdf("docs/sql-query-explanation.pdf")
