import json

from django.core.exceptions import RequestDataTooBig
from django.http import JsonResponse


def response(data, status=200):
    result = JsonResponse(data, status=status)
    result["Cache-Control"] = "no-store"
    return result


def body_json(request):
    try:
        length = request.META.get("CONTENT_LENGTH", "")
        if str(length).isdigit() and int(length) > 1_000_000:
            raise ValueError("JSON request body exceeds the 1 MB limit.")
        if len(request.body) > 1_000_000:
            raise ValueError("JSON request body exceeds the 1 MB limit.")
        return json.loads(request.body or b"{}")
    except RequestDataTooBig as error:
        raise ValueError("JSON request body exceeds the 1 MB limit.") from error
    except json.JSONDecodeError as error:
        raise ValueError("Malformed JSON request body.") from error


def public_user(user):
    return {
        "id": user.pk,
        "email": user.email,
        "name": user.name,
        "provider": user.provider,
        "role": user.role,
    }


def timestamp(value):
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z") if value else None
