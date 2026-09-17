import io
import json
import re
from unittest.mock import patch

from django.test import TestCase, override_settings


class RecordingStdout(io.StringIO):
    def __init__(self):
        super().__init__()
        self.events = []

    def write(self, value):
        self.events.append(("write", value))
        return super().write(value)

    def flush(self):
        self.events.append(("flush", ""))
        return super().flush()


class DevelopmentOtpLoggingTests(TestCase):
    databases = {"default"}

    @override_settings(DEBUG=True, EMAIL_HOST="")
    def test_signup_otp_is_written_to_stdout_and_flushed_immediately(self):
        email = "new-researcher@example.test"
        stdout = RecordingStdout()

        with patch("sys.stdout", stdout):
            response = self.client.post(
                "/api/auth/signup/request",
                data=json.dumps(
                    {
                        "name": "New Researcher",
                        "email": email,
                        "password": "development-password",
                    }
                ),
                content_type="application/json",
            )

        self.assertLess(response.status_code, 300, response.content)

        otp_matches = re.findall(r"(?<!\d)\d{6}(?!\d)", stdout.getvalue())
        self.assertEqual(len(otp_matches), 1, stdout.getvalue())

        confirmation = self.client.post(
            "/api/auth/signup/confirm",
            data=json.dumps({"email": email, "otp": otp_matches[0]}),
            content_type="application/json",
        )
        self.assertLess(confirmation.status_code, 300, confirmation.content)

        otp_write_index = next(
            index
            for index, (event, value) in enumerate(stdout.events)
            if event == "write" and re.search(r"(?<!\d)\d{6}(?!\d)", value)
        )
        flush_index = next(
            index for index, (event, _value) in enumerate(stdout.events) if event == "flush"
        )
        self.assertLess(otp_write_index, flush_index)
        self.assertTrue(
            all(
                event == "write" and not value.strip()
                for event, value in stdout.events[otp_write_index + 1 : flush_index]
            ),
            stdout.events,
        )
