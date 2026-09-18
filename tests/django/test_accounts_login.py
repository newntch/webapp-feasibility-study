import json

from django.core.management import call_command
from django.test import TestCase, override_settings

DEMO_EMAIL = "researcher@example.com"
DEMO_PASSWORD = "ChangeMe123!"


class DemoLoginTests(TestCase):
    databases = {"default"}

    @override_settings(DEMO_ACCOUNT_ENABLED=True)
    def test_advertised_demo_credentials_authenticate_after_application_provisioning(self):
        login_page = self.client.get("/login.html")
        self.assertEqual(login_page.status_code, 200)
        page_html = b"".join(login_page.streaming_content).decode()
        self.assertIn(DEMO_EMAIL, page_html)
        self.assertIn(DEMO_PASSWORD, page_html)

        call_command("ensure_demo_user")

        response = self.client.post(
            "/api/auth/login",
            data=json.dumps({"email": DEMO_EMAIL, "password": DEMO_PASSWORD}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["user"]["email"], DEMO_EMAIL)
        self.assertIn("cohort_lens_session", self.client.cookies)
