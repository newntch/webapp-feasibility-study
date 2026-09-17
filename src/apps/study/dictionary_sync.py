"""Fetch the public vocabulary snapshot used by the dictionary page.

This is a source catalog, not patient-level clinical data. The mapping preserves
the published sheet provenance and the former snapshot's JSON contract.
"""

import csv
import io
import re
from urllib.request import Request, urlopen

SOURCES = (
    {
        "key": "icd10",
        "domain": "diagnosis",
        "label": "ICD-10",
        "sheet_id": "1LUkz2iFHE34DK2MLXuZl5EXvWgn3Xikl",
        "gid": "582609863",
    },
    {
        "key": "icd9",
        "domain": "diagnosis",
        "label": "ICD-9",
        "sheet_id": "1P1BlnGh2O972UX5D3xHDC6L6RqyTDNn9",
        "gid": "1234208350",
    },
    {
        "key": "lab",
        "domain": "lab",
        "label": "Lab",
        "sheet_id": "1hIld3JpJ4JfsCElOoxBsfsODlQD8z5O_",
        "gid": "201536504",
    },
    {
        "key": "drug",
        "domain": "drug",
        "label": "Drug",
        "sheet_id": "1dH-J71VZFE9YV8gSxbH-nqdc2rXRmJXx",
        "gid": "959152876",
    },
)


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_csv(csv_text):
    """Parse published CSV headers into stable snake_case keys."""
    rows = csv.reader(io.StringIO(csv_text, newline=""))
    headers = next(rows, None)
    if headers is None:
        return []
    keys = [re.sub(r"[^a-z0-9]+", "_", _clean(h).lower()).strip("_") for h in headers]
    return [
        dict(zip(keys, (row + [""] * len(keys)), strict=False))
        for row in rows
        if any(_clean(cell) for cell in row)
    ]


def _number_or_none(value):
    cleaned = re.sub(r"[^0-9.\-]", "", str(value or ""))
    if not cleaned:
        return 0
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def normalize_source_rows(source, rows):
    """Keep the prior JSON shape, dropping blank code/name rows."""
    entries = []
    for row in rows:
        key = source["key"]
        if key == "icd10":
            code, name, group, count = (
                _clean(row.get("icd_code")),
                _clean(row.get("disease_name")),
                "ICD-10",
                None,
            )
        elif key == "icd9":
            code, name, group, count = (
                _clean(row.get("icdcm_code")),
                _clean(row.get("icdcm_desc")),
                "ICD-9",
                None,
            )
        elif key == "lab":
            label = _clean(row.get("lab_code"))
            match = re.match(r"^\(([^)]+)\)\s*(.+)$", label)
            code, name = (_clean(match[1]), _clean(match[2])) if match else (label, label)
            group, count = _clean(row.get("group_name")), None
        elif key == "drug":
            code, name = _clean(row.get("generic_id")), _clean(row.get("generic_name"))
            group = " / ".join(
                part
                for part in (_clean(row.get("nlem_cls1")), _clean(row.get("nlem_cls2")))
                if part
            )
            count = _number_or_none(row.get("number_of_drugs"))
        else:
            continue
        if code or name:
            entries.append({"code": code, "name": name, "groupName": group, "count": count})
    return entries


def _fetch_text(url):
    request = Request(url, headers={"Accept": "text/csv,text/plain;q=0.9,*/*;q=0.1"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8-sig")


def fetch_remote_dictionary(fetch_text=None):
    """Fetch all sources before returning, so no partial snapshot is published."""
    fetch_text = fetch_text or _fetch_text
    catalog = {"diagnosis": [], "lab": [], "drug": []}
    provenance = []
    for source in SOURCES:
        link = (
            f"https://docs.google.com/spreadsheets/d/{source['sheet_id']}/edit"
            f"?gid={source['gid']}#gid={source['gid']}"
        )
        url = (
            f"https://docs.google.com/spreadsheets/d/{source['sheet_id']}/export"
            f"?format=csv&gid={source['gid']}"
        )
        catalog[source["domain"]].extend(normalize_source_rows(source, parse_csv(fetch_text(url))))
        provenance.append(
            {
                "key": source["key"],
                "domain": source["domain"],
                "label": source["label"],
                "link": link,
            }
        )
    for domain, entries in catalog.items():
        merged = {}
        for entry in entries:
            key = (entry["code"], entry["name"], entry["groupName"])
            if key not in merged:
                merged[key] = entry
            elif merged[key]["count"] is None and entry["count"] is not None:
                merged[key]["count"] = entry["count"]
        catalog[domain] = sorted(merged.values(), key=lambda item: (item["code"], item["name"]))
    return {"conceptCatalog": catalog, "sources": provenance}
