import uuid

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import connections, models
from django.utils import timezone

from apps.study.clinical import ensure_clinical_ready, run_feasibility
from apps.study.clinical_sql import build_count_query
from apps.study.models import AuditSession, FeasibilityRun, SavedCohort
from config.http import body_json, public_user, response, timestamp


def require_user(request):
    if not request.user.is_authenticated:
        return response({"error": "Not authenticated"}, 401)
    return None


def cohort_json(item):
    return {
        "id": item.pk,
        "userId": item.user_id,
        "name": item.name,
        "savedAt": timestamp(item.saved_at),
        "config": item.config,
    }


def audit_json(item):
    return {
        "id": item.pk,
        "startedAt": timestamp(item.started_at),
        "lastSeenAt": timestamp(item.last_seen_at),
        "pageViews": item.page_views,
        "runCount": item.run_count,
        "user": public_user(item.user) if item.user else None,
        "userAgent": item.user_agent,
    }


def run_json(item):
    result = {
        "id": item.pk,
        "sessionId": item.session_id,
        "user": public_user(item.user) if item.user else None,
        "createdAt": timestamp(item.created_at),
        "question": item.question,
        "indexEligibleCount": item.index_eligible_count,
        "finalCount": item.final_count,
        "excludedCount": item.excluded_count,
        "attrition": item.attrition,
        "selectedConcepts": item.selected_concepts,
        "config": item.config,
        "sql": item.sql,
        "dataSource": item.data_source,
    }
    if item.dataset_version:
        result["datasetVersion"] = item.dataset_version
    return result


def cohorts(request):
    denied = require_user(request)
    if denied:
        return denied
    if request.method == "GET":
        items = SavedCohort.objects.filter(user=request.user, deleted_at__isnull=True).order_by(
            "-saved_at"
        )
        return response({"cohorts": [cohort_json(item) for item in items]})
    try:
        body = body_json(request)
        if not body.get("name") or not isinstance(body.get("config"), dict):
            return response({"error": "Name and config are required"}, 400)
        item = SavedCohort.objects.create(
            id=str(body.get("id") or uuid.uuid4()),
            user=request.user,
            name=str(body["name"])[:200],
            config=body["config"],
            saved_at=timezone.now(),
        )
        return response({"cohort": cohort_json(item)}, 201)
    except ValueError as error:
        return response({"error": str(error)}, 400)


def cohort_delete(request, cohort_id):
    denied = require_user(request)
    if denied:
        return denied
    SavedCohort.objects.filter(pk=cohort_id, user=request.user).delete()
    return response({}, 204)


def audit_session(request):
    denied = require_user(request)
    if denied:
        return denied
    key = request.session.session_key
    if not key:
        request.session.save()
        key = request.session.session_key
    item, created = AuditSession.objects.get_or_create(
        pk=key,
        defaults={
            "user": request.user,
            "started_at": timezone.now(),
            "last_seen_at": timezone.now(),
            "page_views": 0,
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:512],
        },
    )
    item.page_views += 1
    item.last_seen_at = timezone.now()
    item.save(update_fields=["page_views", "last_seen_at"])
    return response({"session": audit_json(item)})


def audit_run(request):
    denied = require_user(request)
    if denied:
        return denied
    try:
        body = body_json(request)
        item = FeasibilityRun.objects.create(
            id=str(body.get("id") or uuid.uuid4()),
            user=request.user,
            session_id=request.session.session_key or "",
            created_at=timezone.now(),
            question=str(body.get("question") or ""),
            index_eligible_count=int(body.get("indexEligibleCount") or 0),
            final_count=int(body.get("finalCount") or 0),
            excluded_count=int(body.get("excludedCount") or 0),
            attrition=body.get("attrition") or [],
            selected_concepts=body.get("selectedConcepts") or {},
            config=body.get("config") or {},
            sql=str(body.get("sql") or ""),
            data_source="omop-postgres",
            dataset_version=str(body.get("datasetVersion") or settings.CLINICAL_DATASET_VERSION),
        )
        AuditSession.objects.filter(pk=item.session_id, user=request.user).update(
            run_count=models.F("run_count") + 1, last_seen_at=timezone.now()
        )
        return response({"run": run_json(item)}, 201)
    except (ValueError, TypeError) as error:
        return response({"error": str(error)}, 400)


def logs(request):
    denied = require_user(request)
    if denied:
        return denied
    if request.method == "DELETE":
        FeasibilityRun.objects.filter(user=request.user).delete()
        AuditSession.objects.filter(user=request.user).delete()
        return response({"ok": True})
    sessions = (
        AuditSession.objects.filter(user=request.user)
        .select_related("user")
        .order_by("-started_at")
    )
    runs = (
        FeasibilityRun.objects.filter(user=request.user)
        .select_related("user")
        .order_by("-created_at")
    )
    return response(
        {
            "sessions": [audit_json(item) for item in sessions],
            "runs": [run_json(item) for item in runs],
        }
    )


def feasibility_run(request):
    denied = require_user(request)
    if denied:
        return denied
    try:
        body = body_json(request)
        result = run_feasibility(body.get("config") or {})
        metadata = {
            "dataSource": "omop-postgres",
            "datasetVersion": settings.CLINICAL_DATASET_VERSION,
        }
        return response(
            {"dataSource": "omop-postgres", "metadata": metadata, "result": result, "data": result}
        )
    except ValueError as error:
        return response({"error": str(error)}, 400)
    except Exception:
        return response({"error": "Unable to run feasibility query"}, 503)


def feasibility_preview(request):
    denied = require_user(request)
    if denied:
        return denied
    try:
        body = body_json(request)
        query, _ = build_count_query(body.get("config") or {})
        return response({"sql": query.replace("%%", "%")})
    except ValueError as error:
        return response({"error": str(error)}, 400)


def cohort_request(request):
    denied = require_user(request)
    if denied:
        return denied
    try:
        body = body_json(request)
        email = str(body.get("email", "")).strip()
        name = str(body.get("name", "")).strip()
        reason = str(body.get("requestReason", "")).strip()
        if not email or "@" not in email or not name or not reason:
            return response({"error": "Email, name-surname, and request reason are required."}, 400)
        if not settings.EMAIL_HOST:
            return response(
                {
                    "ok": True,
                    "mode": "console",
                    "message": "SMTP is not configured; request was not sent.",
                }
            )
        summary = (
            f"Requester: {name} <{email}>\nReason: {reason}\n"
            f"Question: {str(body.get('question') or '')}\n"
            f"Index eligible: {int(body.get('indexEligibleCount') or 0)}\n"
            f"Final count: {int(body.get('finalCount') or 0)}\n"
            f"Excluded count: {int(body.get('excludedCount') or 0)}\n"
            f"SQL preview:\n{str(body.get('sql') or '')}\n"
        )
        message = EmailMessage(
            "Cohort feasibility request", summary, settings.DEFAULT_FROM_EMAIL, [email]
        )
        svg = body.get("workflowSvg")
        if svg:
            message.attach("cohort-workflow.svg", str(svg), "image/svg+xml")
        message.send(fail_silently=False)
        return response({"ok": True, "mode": "email", "message": f"Request sent to {email}."})
    except (ValueError, TypeError) as error:
        return response({"error": str(error)}, 400)
    except Exception:
        return response({"error": "Unable to send cohort request email."}, 503)


def health(request):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        ensure_clinical_ready()
        return response({"ok": True})
    except Exception:
        return response({"ok": False}, 503)
