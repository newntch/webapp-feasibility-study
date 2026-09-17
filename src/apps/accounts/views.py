import json
import secrets
import uuid
from datetime import timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import bcrypt
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie

from apps.accounts.models import User
from apps.study.models import PendingOtp
from config.http import body_json, public_user, response


@ensure_csrf_cookie
def me(request):
    if not request.user.is_authenticated:
        return response({"error": "Not authenticated"}, 401)
    return response({"user": public_user(request.user)})


def credential_login(request):
    try:
        body = body_json(request)
    except ValueError as error:
        return response({"error": str(error)}, 400)
    user = authenticate(
        request, email=str(body.get("email", "")).strip().lower(), password=body.get("password")
    )
    if user is None:
        return response({"error": "Invalid email or password"}, 401)
    login(request, user)
    return response({"user": public_user(user)})


def credential_logout(request):
    logout(request)
    return response({"ok": True})


def send_otp(email, purpose, payload, user=None):
    if not settings.EMAIL_HOST and not settings.DEBUG:
        raise RuntimeError("SMTP is required outside local development")
    code = f"{secrets.randbelow(1_000_000):06d}"
    PendingOtp.objects.update_or_create(
        purpose=purpose,
        email=email,
        defaults={
            "user": user,
            "otp_hash": bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode(),
            "attempts": 0,
            "expires_at": timezone.now() + timedelta(minutes=10),
            "payload": payload,
        },
    )
    if not settings.EMAIL_HOST:
        print(f"Development OTP: {code}", flush=True)
        return "console"
    send_mail(
        "Cohort Lens verification code",
        f"Your code is {code}",
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )
    return "email"


def verify_otp(purpose, email, code):
    record = PendingOtp.objects.filter(purpose=purpose, email=email).first()
    if not record or record.expires_at <= timezone.now() or record.attempts >= 5:
        return None
    record.attempts += 1
    record.save(update_fields=["attempts"])
    return record if bcrypt.checkpw(str(code).encode(), record.otp_hash.encode()) else None


def signup_request(request):
    try:
        body = body_json(request)
        email = str(body.get("email", "")).strip().lower()
        name = str(body.get("name", "")).strip()
        password = str(body.get("password", ""))
        if not email or not name or len(password) < 8:
            return response(
                {"error": "Name, email and password of at least 8 characters are required"}, 400
            )
        if User.objects.filter(email=email).exists():
            return response({"error": "Email is already registered"}, 409)
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        mode = send_otp(email, "signup", {"name": name, "passwordHash": hashed})
        return response({"ok": True, "mode": mode})
    except (ValueError, RuntimeError) as error:
        return response({"error": str(error)}, 400)


def signup_confirm(request):
    try:
        body = body_json(request)
        email = str(body.get("email", "")).strip().lower()
        record = verify_otp("signup", email, body.get("otp", ""))
        if not record:
            return response({"error": "Invalid or expired OTP"}, 400)
        user = User.objects.create_user(
            email=email,
            id=f"user-{uuid.uuid4()}",
            name=record.payload["name"],
            password=None,
            provider="credentials",
        )
        user.password = f"bcrypt${record.payload['passwordHash']}"
        user.save(update_fields=["password"])
        record.delete()
        login(request, user)
        return response({"user": public_user(user)})
    except ValueError as error:
        return response({"error": str(error)}, 400)


def password_request(request):
    try:
        body = body_json(request)
        email = str(body.get("email", "")).strip().lower()
        user = User.objects.filter(email=email, is_active=True).first()
        if user:
            send_otp(email, "password", {}, user)
        return response({"ok": True})
    except (ValueError, RuntimeError) as error:
        return response({"error": str(error)}, 400)


def password_confirm(request):
    try:
        body = body_json(request)
        email = str(body.get("email", "")).strip().lower()
        password = str(body.get("password", ""))
        if len(password) < 8:
            return response({"error": "Password must have at least 8 characters"}, 400)
        record = verify_otp("password", email, body.get("otp", ""))
        if not record or not record.user:
            return response({"error": "Invalid or expired OTP"}, 400)
        record.user.set_password(password)
        record.user.password_updated_at = timezone.now()
        record.user.save(update_fields=["password", "password_updated_at"])
        record.delete()
        return response({"ok": True})
    except ValueError as error:
        return response({"error": str(error)}, 400)


def google_start(request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return HttpResponse("Google OAuth is not configured", status=503)
    state = secrets.token_urlsafe(32)
    redirect_uri = settings.GOOGLE_REDIRECT_URI or request.build_absolute_uri(
        "/api/auth/google/callback"
    )
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
    )
    result = HttpResponseRedirect(url)
    result.set_cookie(
        "cohort_lens_oauth_state",
        state,
        max_age=600,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="Lax",
    )
    return result


def google_callback(request):
    expected = request.COOKIES.get("cohort_lens_oauth_state")
    state = request.GET.get("state")
    code = request.GET.get("code")
    if not expected or not secrets.compare_digest(expected, state or "") or not code:
        return HttpResponse("Invalid Google OAuth callback state", status=400)
    redirect_uri = settings.GOOGLE_REDIRECT_URI or request.build_absolute_uri(
        "/api/auth/google/callback"
    )
    payload = urlencode(
        {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode()
    try:
        token_request = Request(
            "https://oauth2.googleapis.com/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urlopen(token_request, timeout=15) as result:
            token = json.load(result)
        profile_request = Request(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token['access_token']}"},
        )
        with urlopen(profile_request, timeout=15) as result:
            profile = json.load(result)
    except (OSError, ValueError, KeyError):
        return HttpResponse("Google OAuth exchange failed", status=502)
    email = str(profile.get("email", "")).strip().lower()
    google_sub = profile.get("sub")
    if not email or not google_sub or not profile.get("email_verified"):
        return HttpResponse("Google email must be verified", status=403)
    if settings.GOOGLE_ALLOWED_EMAILS and email not in settings.GOOGLE_ALLOWED_EMAILS:
        return HttpResponse("Google account is not allowed", status=403)
    user = User.objects.filter(google_sub=google_sub).first()
    if user is None:
        user = User.objects.filter(email=email).first()
    if user is not None and not user.is_active:
        return HttpResponse("Google account is inactive", status=403)
    if user is None:
        user = User.objects.create_user(
            email=email,
            id=f"user-{uuid.uuid4()}",
            name=profile.get("name") or email,
            provider="google",
            google_sub=google_sub,
        )
    else:
        user.email = email
        user.name = profile.get("name") or email
        user.google_sub = google_sub
        user.provider = "google"
        user.save(update_fields=["email", "name", "google_sub", "provider"])
    login(request, user)
    result = HttpResponseRedirect("/")
    result.delete_cookie("cohort_lens_oauth_state")
    return result
