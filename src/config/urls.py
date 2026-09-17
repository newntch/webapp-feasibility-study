from django.conf import settings
from django.http import FileResponse, HttpResponseNotFound
from django.urls import path, re_path
from django.views.decorators.csrf import ensure_csrf_cookie

from apps.accounts import views as auth
from apps.study import views as study
from config.http import response

PAGES = {
    "": "index.html",
    "index.html": "index.html",
    "login.html": "login.html",
    "logs.html": "logs.html",
    "dictionary.html": "dictionary.html",
}
MODULES = {
    "cohort/advancedConditions.js",
    "cohort/cohortEngine.js",
    "dictionary/masterDictionary.js",
    "filters/filterBuilderBehavior.js",
    "filters/filterBuilderDefaults.js",
    "sql/omopSqlBuilder.js",
    "sql/sqlBuilder.js",
}


@ensure_csrf_cookie
def page(request, name=""):
    if name not in PAGES:
        return HttpResponseNotFound("Not found")
    return FileResponse(
        (settings.BASE_DIR / "public" / PAGES[name]).open("rb"), content_type="text/html"
    )


def module(request, name):
    if name not in MODULES:
        return HttpResponseNotFound("Not found")
    return FileResponse(
        (settings.BASE_DIR / "src" / "core" / name).open("rb"), content_type="text/javascript"
    )


def asset(request, name):
    root = settings.BASE_DIR / "public" / "assets"
    target = (root / name).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        return HttpResponseNotFound("Not found")
    mime = "text/javascript" if target.suffix == ".js" else "text/css"
    return FileResponse(target.open("rb"), content_type=mime)


def dictionary_data(request):
    target = settings.BASE_DIR / "public" / "data" / "master-dictionary.json"
    return FileResponse(target.open("rb"), content_type="application/json")


def unknown_api(request):
    return response({"error": "API route not found"}, 404)


urlpatterns = [
    path("", page),
    path("index.html", page, {"name": "index.html"}),
    path("login.html", page, {"name": "login.html"}),
    path("logs.html", page, {"name": "logs.html"}),
    path("dictionary.html", page, {"name": "dictionary.html"}),
    path("api/auth/me", auth.me),
    path("api/auth/login", auth.credential_login),
    path("api/auth/logout", auth.credential_logout),
    path("api/auth/signup/request", auth.signup_request),
    path("api/auth/signup/confirm", auth.signup_confirm),
    path("api/auth/password/request", auth.password_request),
    path("api/auth/password/confirm", auth.password_confirm),
    path("api/auth/google", auth.google_start),
    path("api/auth/google/callback", auth.google_callback),
    path("api/bootstrap", study.bootstrap),
    path("api/health", study.health),
    path("api/feasibility/run", study.feasibility_run),
    path("api/feasibility/preview", study.feasibility_preview),
    path("api/cohort-request", study.cohort_request),
    path("api/audit/session", study.audit_session),
    path("api/audit/run", study.audit_run),
    path("api/logs", study.logs),
    path("api/cohorts", study.cohorts),
    path("api/cohorts/<str:cohort_id>", study.cohort_delete),
    re_path(r"^modules/(?P<name>[^?]+)$", module),
    re_path(r"^assets/(?P<name>[^?]+)$", asset),
    path("data/master-dictionary.json", dictionary_data),
    re_path(r"^api/.*$", unknown_api),
]
