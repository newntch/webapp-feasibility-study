"""Refresh the public dictionary snapshot without a JavaScript toolchain."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.study.dictionary_sync import fetch_remote_dictionary


class Command(BaseCommand):
    help = "Refresh the public diagnosis, lab, and drug dictionary snapshot."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-path", default=str(settings.BASE_DIR / "public/data/master-dictionary.json")
        )

    def handle(self, *args, **options):
        target = Path(options["output_path"]).resolve()
        try:
            payload = fetch_remote_dictionary()
        except OSError as exc:
            raise CommandError(f"Dictionary fetch failed: {exc}") from exc
        document = {
            "mode": "local-file",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_dir = settings.BASE_DIR / "temp"
        temporary_dir.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=temporary_dir, prefix="dictionary-", delete=False
            ) as handle:
                temporary = Path(handle.name)
                json.dump(document, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            temporary.chmod(0o644)
            os.replace(temporary, target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.stdout.write(f"Wrote {target}")
