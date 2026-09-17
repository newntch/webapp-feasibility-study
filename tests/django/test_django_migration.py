"""Compatibility checks for the Express-to-Django application migration.

Fixtures are synthetic and intentionally contain no patient-level data.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import CommandError, call_command
from django.test import Client, TestCase

from apps.accounts.models import User

BCRYPT_HASH = "$2b$04$QtSgUiMGs18w/6ZCNFxIpOLqaiaWXKPlxdK/Fvs7Nj73.ZZLr11Ce"
USER = {
    "id": "user-synthetic-1",
    "email": "researcher@example.test",
    "name": "Synthetic Researcher",
    "role": "researcher",
    "provider": "credentials",
    "googleSub": None,
    "passwordHash": BCRYPT_HASH,
    "active": True,
    "createdAt": "2025-01-02T03:04:05.000Z",
    "passwordUpdatedAt": "2025-01-03T03:04:05.000Z",
    "lastLoginAt": None,
}
PUBLIC_USER = {
    "id": USER["id"],
    "email": USER["email"],
    "name": USER["name"],
    "provider": USER["provider"],
    "role": USER["role"],
}
SAVED_COHORT = {
    "id": "cohort-synthetic-1",
    "userId": USER["id"],
    "name": "Synthetic adult cohort",
    "savedAt": "2025-02-03T04:05:06.000Z",
    "config": {"minimumAge": 18, "selectedConcepts": {"condition": [123]}},
}
AUDIT_SESSION = {
    "id": "legacy-session-synthetic-1",
    "startedAt": "2025-02-03T04:05:06.000Z",
    "lastSeenAt": "2025-02-03T05:05:06.000Z",
    "pageViews": 2,
    "runCount": 1,
    "user": PUBLIC_USER,
    "userAgent": "synthetic-test-agent",
}
RUN_LOG = {
    "id": "run-synthetic-1",
    "sessionId": AUDIT_SESSION["id"],
    "user": PUBLIC_USER,
    "createdAt": "2025-02-03T05:00:00.000Z",
    "question": "Synthetic research question",
    "indexEligibleCount": 10,
    "finalCount": 7,
    "excludedCount": 3,
    "attrition": [{"label": "Eligible", "count": 10}],
    "selectedConcepts": {"condition": [123]},
    "config": SAVED_COHORT["config"],
    "sql": "SELECT 7",
    "dataSource": "omop-duckdb",
}


class ApplicationJsonMigrationTests(TestCase):
    """Import durable app data without reviving legacy credentials."""

    databases = {"default"}

    def setUp(self):
        Path("temp").mkdir(exist_ok=True)
        self.source = TemporaryDirectory(prefix="app-json-test-", dir="temp")
        self.addCleanup(self.source.cleanup)
        self.source_path = Path(self.source.name)
        self.write_source()

    def write_source(self):
        records = {
            "users.json": [USER],
            "saved-cohorts.json": [SAVED_COHORT],
            "audit-session-logs.json": [AUDIT_SESSION],
            "feasibility-run-logs.json": [RUN_LOG],
            "user-sessions.json": [
                {
                    "sessionId": AUDIT_SESSION["id"],
                    "userId": USER["id"],
                    "expiresAt": "2099-01-01T00:00:00.000Z",
                }
            ],
            "pending-otps.json": [
                {
                    "purpose": "signup",
                    "email": "pending@example.test",
                    "otpHash": "synthetic-not-a-real-otp-hash",
                    "attempts": 0,
                    "expiresAt": "2099-01-01T00:00:00.000Z",
                }
            ],
        }
        for filename, value in records.items():
            (self.source_path / filename).write_text(json.dumps(value), encoding="utf-8")

    def import_source(self):
        call_command("import_app_json", source_dir=str(self.source_path), verbosity=0)

    def login(self):
        return self.client.post(
            "/api/auth/login",
            data=json.dumps({"email": " Researcher@Example.Test ", "password": "correct-password"}),
            content_type="application/json",
        )

    def test_import_preserves_identity_bcrypt_and_durable_records(self):
        self.import_source()

        user = User.objects.get(pk=USER["id"])
        self.assertEqual(user.email, USER["email"])
        self.assertTrue(user.check_password("correct-password"))
        self.assertFalse(user.check_password("incorrect-password"))

        login = self.login()
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json(), {"user": PUBLIC_USER})

        cohorts = self.client.get("/api/cohorts")
        self.assertEqual(cohorts.status_code, 200)
        self.assertEqual(cohorts.json(), {"cohorts": [SAVED_COHORT]})

        logs = self.client.get("/api/logs")
        self.assertEqual(logs.status_code, 200)
        self.assertEqual(logs.json()["sessions"], [AUDIT_SESSION])
        self.assertEqual(logs.json()["runs"], [RUN_LOG])

    def test_import_is_idempotent_and_legacy_session_is_not_authentication(self):
        self.import_source()
        self.import_source()

        self.assertEqual(User.objects.filter(pk=USER["id"]).count(), 1)
        self.client.cookies["cohort_lens_session"] = AUDIT_SESSION["id"]
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.client.cookies.clear()

        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(len(self.client.get("/api/cohorts").json()["cohorts"]), 1)
        logs = self.client.get("/api/logs").json()
        self.assertEqual(len(logs["sessions"]), 1)
        self.assertEqual(len(logs["runs"]), 1)

    def test_malformed_source_stops_without_partial_import(self):
        (self.source_path / "saved-cohorts.json").write_text("{malformed", encoding="utf-8")

        with self.assertRaises(CommandError):
            self.import_source()

        self.assertFalse(User.objects.filter(pk=USER["id"]).exists())

    def test_browser_login_and_audit_post_require_csrf_token(self):
        self.import_source()
        browser = Client(enforce_csrf_checks=True)

        login_page = browser.get("/login.html")
        self.assertEqual(login_page.status_code, 200)
        self.assertIn("csrftoken", browser.cookies)
        csrf_token = browser.cookies["csrftoken"].value

        login = browser.post(
            "/api/auth/login",
            data=json.dumps({"email": USER["email"], "password": "correct-password"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("cohort_lens_session", browser.cookies)
        self.assertEqual(browser.get("/api/auth/me").json(), {"user": PUBLIC_USER})

        audit = browser.post(
            "/api/audit/session",
            data="{}",
            content_type="application/json",
            HTTP_X_CSRFTOKEN=browser.cookies["csrftoken"].value,
        )
        self.assertEqual(audit.status_code, 200)
        self.assertIn("session", audit.json())

        missing_token = browser.post(
            "/api/audit/session", data="{}", content_type="application/json"
        )
        self.assertEqual(missing_token.status_code, 403)


class DjangoApiContractTests(TestCase):
    databases = {"default"}

    def test_protected_routes_keep_json_401_contract(self):
        for path in ("/api/auth/me", "/api/cohorts", "/api/logs"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"error": "Not authenticated"})
                self.assertEqual(response["Cache-Control"], "no-store")

    def test_unknown_api_route_is_json_404(self):
        response = self.client.get("/api/not-a-route")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "API route not found"})
