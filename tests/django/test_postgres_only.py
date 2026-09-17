"""Contracts for the PostgreSQL-only application surface."""

import re
from pathlib import Path

from django.test import Client, TestCase

ROOT = Path(__file__).resolve().parents[2]


class PostgreSqlOnlyRoutesTests(TestCase):
    databases = {"default"}

    def test_removed_legacy_routes_are_not_available(self):
        for path in ("/dictionary.html", "/data/master-dictionary.json"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)
        response = self.client.get("/api/bootstrap")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "API route not found"})

    def test_protected_routes_keep_json_401_contract(self):
        for path in ("/api/auth/me", "/api/cohorts", "/api/logs"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"error": "Not authenticated"})
                self.assertEqual(response["Cache-Control"], "no-store")


def test_legacy_data_sources_are_not_in_runtime_or_dependencies():
    assert "duckdb" not in (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    assert "./data:/app/data:ro" not in (ROOT / "compose.yaml").read_text(encoding="utf-8")
    for path in (
        "src/apps/study/management/commands/import_app_json.py",
        "src/apps/study/management/commands/import_clinical_duckdb.py",
        "src/apps/study/management/commands/sync_dictionary.py",
        "public/dictionary.html",
        "public/data/master-dictionary.json",
    ):
        assert not (ROOT / path).exists(), path


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
                raise AssertionError(
                    f"Unresolved/bare browser import in {script.name}: {specifier}"
                )
            assert client.get(url).status_code == 200, f"{script.name} imports missing {url}"
