from pathlib import Path


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
LEFT = 52
RIGHT = 52
TOP = 790
BOTTOM = 48
BODY_WIDTH = 91
CODE_WIDTH = 108
OUTPUT = Path("docs/omop-all-conditions-query.pdf")


QUERY = """WITH PersonBase AS (
  SELECT
    person_id,
    CASE
      WHEN birth_datetime IS NOT NULL
        THEN CAST(birth_datetime AS DATE)
      WHEN year_of_birth IS NOT NULL
       AND month_of_birth IS NOT NULL
       AND day_of_birth IS NOT NULL
        THEN MAKE_DATE(
          CAST(year_of_birth AS INTEGER),
          CAST(month_of_birth AS INTEGER),
          CAST(day_of_birth AS INTEGER)
        )
    END AS birth_date
  FROM person
),

IndexEvents AS (
  SELECT
    co.person_id,
    CAST(co.condition_start_date AS DATE) AS event_date
  FROM condition_occurrence co
  JOIN concept c
    ON c.concept_id = co.condition_concept_id
  WHERE c.concept_code = '59621000'
    AND co.condition_start_date IS NOT NULL
    AND CAST(co.condition_start_date AS DATE)
        BETWEEN DATE '2020-01-01' AND DATE '2023-12-31'
),

IndexCohort AS (
  SELECT
    person_id,
    MIN(event_date) AS t0_date
  FROM IndexEvents
  GROUP BY person_id
),

BasePatients AS (
  SELECT
    p.person_id,
    i.t0_date
  FROM PersonBase p
  JOIN IndexCohort i
    ON i.person_id = p.person_id
  WHERE DATE_DIFF('year', p.birth_date, i.t0_date)
        BETWEEN 18 AND 75
),

LabInclusion AS (
  SELECT DISTINCT
    b.person_id
  FROM BasePatients b
  JOIN measurement m
    ON m.person_id = b.person_id
  JOIN concept c
    ON c.concept_id = m.measurement_concept_id
  WHERE c.concept_code = '8480-6'
    AND m.measurement_date IS NOT NULL
    AND m.value_as_number >= 120
    AND DATE_DIFF(
          'day',
          b.t0_date,
          CAST(m.measurement_date AS DATE)
        ) BETWEEN 0 AND 180
),

DrugInclusion AS (
  SELECT DISTINCT
    b.person_id
  FROM BasePatients b
  JOIN drug_exposure d
    ON d.person_id = b.person_id
  JOIN concept c
    ON c.concept_id = d.drug_concept_id
  WHERE c.concept_code = '861007'
    AND d.drug_exposure_start_date IS NOT NULL
    AND DATE_DIFF(
          'day',
          b.t0_date,
          CAST(d.drug_exposure_start_date AS DATE)
        ) BETWEEN 0 AND 90
),

ExcludedPatients AS (
  SELECT DISTINCT
    b.person_id
  FROM BasePatients b
  JOIN condition_occurrence co
    ON co.person_id = b.person_id
  JOIN concept c
    ON c.concept_id = co.condition_concept_id
  WHERE c.concept_code = '55822004'
    AND co.condition_start_date IS NOT NULL
    AND DATE_DIFF(
          'day',
          b.t0_date,
          CAST(co.condition_start_date AS DATE)
        ) BETWEEN -365 AND 0
),

IncludedCohort AS (
  SELECT b.person_id
  FROM BasePatients b
  JOIN LabInclusion l
    ON l.person_id = b.person_id
  JOIN DrugInclusion d
    ON d.person_id = b.person_id
),

FinalCohort AS (
  SELECT i.person_id
  FROM IncludedCohort i
  WHERE NOT EXISTS (
    SELECT 1
    FROM ExcludedPatients e
    WHERE e.person_id = i.person_id
  )
)

SELECT
  (SELECT COUNT(*) FROM person) AS totalPatients,
  (SELECT COUNT(*) FROM IndexCohort) AS indexEligibleCount,
  (SELECT COUNT(*) FROM BasePatients) AS demographicCount,
  (SELECT COUNT(*) FROM IncludedCohort) AS inclusionCount,
  (SELECT COUNT(*) FROM FinalCohort) AS finalCount;"""


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
    escaped = escape_pdf_text(value)
    return f"BT /{font} {size} Tf 1 0 0 1 {x:.1f} {y:.1f} Tm ({escaped}) Tj ET\n"


def add_footer(pages, commands, page_number):
    commands.append(text_command("F1", 8, LEFT, 27, "Cohort Lens - OMOP All-Conditions Query"))
    commands.append(text_command("F1", 8, PAGE_WIDTH - RIGHT - 34, 27, f"Page {page_number}"))
    pages.append("".join(commands))


def build_pages():
    pages = []
    commands = []
    y = TOP
    page_number = 1

    def new_page():
        nonlocal commands, y, page_number
        add_footer(pages, commands, page_number)
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

    add_line("F2", 19, 25, "Cohort Lens: OMOP All-Conditions Query")
    add_line("F1", 10, 17, "Diagnosis Feasibility Study Webapp")
    add_spacer(8)

    sections = [
        ("heading", "1. Cohort Conditions"),
        ("paragraph", "This document contains the complete OMOP CDM query for the demonstration cohort."),
        ("code", "T0 index: Essential hypertension (SNOMED 59621000)\nIndex window: 2020-01-01 through 2023-12-31\nAge: 18 through 75 years at T0\nInclusion: Systolic blood pressure (LOINC 8480-6) >= 120 within 0-180 days\nInclusion: Metformin (RxNorm 861007) within 0-90 days\nExclusion: Hyperlipidemia (SNOMED 55822004) within -365 to 0 days"),
        ("paragraph", "Sex is unrestricted (Any). T0 is the earliest matching index event for each patient."),
        ("heading", "2. Complete DuckDB Query"),
        ("code", QUERY),
        ("heading", "3. Expected Result"),
        ("code", "totalPatients       6731\nindexEligibleCount  1351\ndemographicCount    1047\ninclusionCount      28\nfinalCount          6"),
        ("paragraph", "The query uses person_id to link events, concept_code to identify standard concepts, DATE_DIFF for timing relative to T0, and separate inclusion and exclusion CTEs for readable cohort logic."),
    ]

    for kind, value in sections:
        if kind == "heading":
            add_spacer(8)
            add_line("F2", 14, 19, value)
            add_spacer(3)
        elif kind == "paragraph":
            for line in wrap_text(value, BODY_WIDTH):
                add_line("F1", 10, 13, line)
            add_spacer(6)
        elif kind == "code":
            add_spacer(3)
            for line in wrap_text(value, CODE_WIDTH):
                add_line("F3", 7.4, 9.4, line, LEFT + 8)
            add_spacer(7)

    if commands:
        add_footer(pages, commands, page_number)
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

    output_path.write_bytes(output)
    print(f"Wrote {output_path} ({len(output)} bytes, {len(pages)} pages)")


if __name__ == "__main__":
    make_pdf(OUTPUT)
