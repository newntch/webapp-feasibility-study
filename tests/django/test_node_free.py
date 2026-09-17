"""Node-free dictionary synchronization and browser asset contracts.

These fixtures contain vocabulary examples only; no patient-level data.
"""

import json
import os
import re
import stat
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command
from django.test import Client

from apps.study.dictionary_sync import fetch_remote_dictionary, parse_csv

ROOT = Path(__file__).resolve().parents[2]
CSV_BY_KEY = {
    "icd10": 'ICD Code,Disease Name\r\nA10,"Synthetic, condition"\r\nA10,"Synthetic, condition"\r\n,\r\n',
    "icd9": "ICDCM Code,ICDCM Desc\nB20,Other synthetic condition\n",
    "lab": 'Lab Code,Group Name\n"(L-1) Synthetic lab",Chemistry\n',
    "drug": (
        "Generic ID,Generic Name,NLEM CLS1,NLEM CLS2,Number of Drugs\n"
        'D-1,Synthetic medicine,Group A,Subclass,"1,234"\n'
    ),
}


def fake_fetch_text(url):
    for key, marker in {
        "icd10": "gid=582609863",
        "icd9": "gid=1234208350",
        "lab": "gid=201536504",
        "drug": "gid=959152876",
    }.items():
        if marker in url:
            return CSV_BY_KEY[key]
    raise AssertionError(f"Unexpected dictionary source URL: {url}")


def test_csv_parser_keeps_quoted_commas_newlines_and_blank_cells():
    rows = parse_csv('Code,Name,Group Name\r\n"C,1","Line 1\nLine 2",\r\n\r\n')
    assert rows == [{"code": "C,1", "name": "Line 1\nLine 2", "group_name": ""}]


def test_remote_dictionary_maps_domains_deduplicates_and_preserves_provenance():
    payload = fetch_remote_dictionary(fetch_text=fake_fetch_text)

    assert payload["conceptCatalog"] == {
        "diagnosis": [
            {"code": "A10", "name": "Synthetic, condition", "groupName": "ICD-10", "count": None},
            {
                "code": "B20",
                "name": "Other synthetic condition",
                "groupName": "ICD-9",
                "count": None,
            },
        ],
        "lab": [{"code": "L-1", "name": "Synthetic lab", "groupName": "Chemistry", "count": None}],
        "drug": [
            {
                "code": "D-1",
                "name": "Synthetic medicine",
                "groupName": "Group A / Subclass",
                "count": 1234,
            }
        ],
    }
    assert [source["key"] for source in payload["sources"]] == ["icd10", "icd9", "lab", "drug"]
    assert all(
        source["link"].startswith("https://docs.google.com/") for source in payload["sources"]
    )
    assert all(set(source) == {"key", "domain", "label", "link"} for source in payload["sources"])


def test_fetch_failure_raises_instead_of_returning_partial_catalog():
    def fail_on_lab(url):
        if "gid=201536504" in url:
            raise OSError("Synthetic fetch failure")
        return fake_fetch_text(url)

    with pytest.raises(OSError, match="Synthetic fetch failure"):
        fetch_remote_dictionary(fetch_text=fail_on_lab)


def test_sync_command_writes_versioned_local_snapshot_without_network():
    (ROOT / "temp").mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="dictionary-test-", dir=ROOT / "temp") as directory:
        output = Path(directory) / "master-dictionary.json"
        with patch(
            "apps.study.management.commands.sync_dictionary.fetch_remote_dictionary",
            return_value=fetch_remote_dictionary(fetch_text=fake_fetch_text),
        ):
            call_command("sync_dictionary", output_path=str(output), verbosity=0)

        document = json.loads(output.read_text(encoding="utf-8"))
        assert document["mode"] == "local-file"
        assert re.fullmatch(
            r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|\+00:00)", document["generatedAt"]
        )
        assert document["conceptCatalog"]["diagnosis"][0]["code"] == "A10"
        assert len(document["sources"]) == 4


def test_failed_sync_preserves_last_good_snapshot():
    (ROOT / "temp").mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="dictionary-test-", dir=ROOT / "temp") as directory:
        output = Path(directory) / "master-dictionary.json"
        previous = '{"mode":"local-file","generatedAt":"2025-01-01T00:00:00Z"}\n'
        output.write_text(previous, encoding="utf-8")
        with patch(
            "apps.study.management.commands.sync_dictionary.fetch_remote_dictionary",
            side_effect=OSError("Synthetic fetch failure"),
        ):
            with pytest.raises((CommandError, OSError), match="Synthetic fetch failure"):
                call_command("sync_dictionary", output_path=str(output), verbosity=0)
        assert output.read_text(encoding="utf-8") == previous


def test_sync_atomically_replaces_snapshot_with_container_readable_file():
    """The staging file stays in repo temp and final data is world-readable."""
    (ROOT / "temp").mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="dictionary-test-", dir=ROOT / "temp") as directory:
        output_dir = Path(directory)
        output_dir.chmod(0o755)
        output = output_dir / "master-dictionary.json"
        output.write_text('{"stale":true}\n', encoding="utf-8")
        replacements = []
        real_replace = os.replace

        def track_replace(source, destination, *args, **kwargs):
            replacements.append((Path(source).resolve(), Path(destination).resolve()))
            return real_replace(source, destination, *args, **kwargs)

        with (
            patch(
                "apps.study.management.commands.sync_dictionary.fetch_remote_dictionary",
                return_value=fetch_remote_dictionary(fetch_text=fake_fetch_text),
            ),
            patch("os.replace", side_effect=track_replace),
        ):
            call_command("sync_dictionary", output_path=str(output), verbosity=0)

        assert replacements, "Snapshot must be committed with an atomic replacement"
        assert any(destination == output.resolve() for _, destination in replacements)
        assert all(source.is_relative_to(ROOT / "temp") for source, _ in replacements)
        assert output.stat().st_mode & stat.S_IROTH
        assert json.loads(output.read_text(encoding="utf-8"))["mode"] == "local-file"


def test_deployment_has_no_node_runtime_or_package_manager():
    for path in (
        "package.json",
        "pnpm-lock.yaml",
        "scripts/dev-server.mjs",
        "scripts/hash-password.mjs",
        "scripts/sync-dictionary.mjs",
        "src/server",
        "tests/integration/expressApp.test.mjs",
    ):
        assert not (ROOT / path).exists(), f"Legacy Node artifact remains: {path}"
    for path in ("Dockerfile", "compose.yaml", "scripts/restart-dev.sh"):
        artifact = ROOT / path
        if not artifact.exists():
            continue
        content = artifact.read_text(encoding="utf-8")
        assert not re.search(r"\b(?:node|npm|pnpm|npx)\b", content, re.IGNORECASE), path


def test_docker_build_context_excludes_local_secrets():
    dockerignore = ROOT / ".dockerignore"
    assert dockerignore.is_file(), "Docker needs an explicit build-context exclusion list"
    entries = {
        line.strip()
        for line in dockerignore.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    for secret in (".env", "config/app.config.json"):
        assert secret in entries, f"Local secret is not excluded from Docker context: {secret}"


def test_browser_module_imports_remain_served_by_django():
    client = Client()
    for script in (ROOT / "public" / "assets" / "js").glob("*.js"):
        content = script.read_text(encoding="utf-8")
        for specifier in re.findall(r"\bfrom\s+['\"]([^'\"]+)['\"]", content):
            if specifier.startswith("/modules/"):
                url = specifier
            elif specifier.startswith("./"):
                url = f"/assets/js/{specifier[2:]}"
            else:
                pytest.fail(f"Unresolved/bare browser import in {script.name}: {specifier}")
            response = client.get(url)
            assert response.status_code == 200, f"{script.name} imports missing {url}"
