import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.study.models import AuditSession, FeasibilityRun, SavedCohort

FILES = {
    "users": "users.json",
    "cohorts": "saved-cohorts.json",
    "sessions": "audit-session-logs.json",
    "runs": "feasibility-run-logs.json",
}


def read_array(path):
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CommandError(f"Malformed JSON in {path.name}") from error
    if not isinstance(data, list):
        raise CommandError(f"Expected a JSON array: {path.name}")
    return data


def parse_time(value):
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def legacy_hash(value):
    if not value:
        return "!"
    if value.startswith("bcrypt$"):
        return value
    if value.startswith(("$2a$", "$2b$", "$2y$")):
        return f"bcrypt${value}"
    raise CommandError("Unrecognized password hash in users.json")


class Command(BaseCommand):
    help = "Import local application JSON into application_db; old sessions and OTPs are excluded."

    def add_arguments(self, parser):
        parser.add_argument("--source-dir", default="data")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        source = Path(options["source_dir"])
        if not source.is_dir():
            raise CommandError(f"Source directory does not exist: {source}")
        records = {key: read_array(source / name) for key, name in FILES.items()}
        ids = {item.get("id") for item in records["users"]}
        if None in ids or len(ids) != len(records["users"]):
            raise CommandError("Users need unique IDs")
        for group in ("cohorts", "sessions", "runs"):
            for item in records[group]:
                user_id = item.get("userId") or (item.get("user") or {}).get("id")
                if user_id and user_id not in ids:
                    raise CommandError(f"{group} contains an unknown user ID")
        counts = {key: len(value) for key, value in records.items()}
        if options["dry_run"]:
            self.stdout.write(json.dumps(counts, sort_keys=True))
            return

        with transaction.atomic():
            for item in records["users"]:
                values = {
                    "email": item["email"].strip().lower(),
                    "name": item.get("name", ""),
                    "role": item.get("role", "researcher"),
                    "provider": item.get("provider", "credentials"),
                    "google_sub": item.get("googleSub"),
                    "password": legacy_hash(item.get("passwordHash")),
                    "is_active": item.get("active", True),
                    "last_login": parse_time(item["lastLoginAt"])
                    if item.get("lastLoginAt")
                    else None,
                    "password_updated_at": parse_time(item["passwordUpdatedAt"])
                    if item.get("passwordUpdatedAt")
                    else None,
                }
                _, created = User.objects.get_or_create(pk=item["id"], defaults=values)
                if created and item.get("createdAt"):
                    User.objects.filter(pk=item["id"]).update(
                        created_at=parse_time(item["createdAt"])
                    )

            for item in records["cohorts"]:
                SavedCohort.objects.get_or_create(
                    pk=item["id"],
                    defaults={
                        "user_id": item["userId"],
                        "name": item["name"],
                        "config": item.get("config") or {},
                        "saved_at": parse_time(item.get("savedAt")),
                    },
                )
            for item in records["sessions"]:
                AuditSession.objects.get_or_create(
                    pk=item["id"],
                    defaults={
                        "user_id": (item.get("user") or {}).get("id"),
                        "started_at": parse_time(item.get("startedAt")),
                        "last_seen_at": parse_time(item.get("lastSeenAt")),
                        "page_views": item.get("pageViews", 0),
                        "run_count": item.get("runCount", 0),
                        "user_agent": item.get("userAgent", ""),
                    },
                )
            for item in records["runs"]:
                FeasibilityRun.objects.get_or_create(
                    pk=item["id"],
                    defaults={
                        "user_id": (item.get("user") or {}).get("id"),
                        "session_id": item.get("sessionId") or "",
                        "created_at": parse_time(item.get("createdAt")),
                        "question": item.get("question") or "",
                        "index_eligible_count": item.get("indexEligibleCount", 0),
                        "final_count": item.get("finalCount", 0),
                        "excluded_count": item.get("excludedCount", 0),
                        "attrition": item.get("attrition") or [],
                        "selected_concepts": item.get("selectedConcepts") or {},
                        "config": item.get("config") or {},
                        "sql": item.get("sql") or "",
                        "data_source": item.get("dataSource") or "omop-duckdb",
                    },
                )
        self.stdout.write(json.dumps(counts, sort_keys=True))
