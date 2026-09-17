from django.conf import settings
from django.db import models


class PendingOtp(models.Model):
    purpose = models.CharField(max_length=30)
    email = models.EmailField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    otp_hash = models.CharField(max_length=255)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["purpose", "email"], name="unique_otp_purpose_email")
        ]


class SavedCohort(models.Model):
    id = models.CharField(max_length=128, primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    config = models.JSONField(default=dict)
    saved_at = models.DateTimeField()
    deleted_at = models.DateTimeField(null=True, blank=True)


class AuditSession(models.Model):
    id = models.CharField(max_length=128, primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    started_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    page_views = models.PositiveIntegerField(default=0)
    run_count = models.PositiveIntegerField(default=0)
    user_agent = models.CharField(max_length=512, blank=True)


class FeasibilityRun(models.Model):
    id = models.CharField(max_length=128, primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    session_id = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField()
    question = models.TextField(blank=True)
    index_eligible_count = models.PositiveIntegerField(default=0)
    final_count = models.PositiveIntegerField(default=0)
    excluded_count = models.PositiveIntegerField(default=0)
    attrition = models.JSONField(default=list)
    selected_concepts = models.JSONField(default=dict)
    config = models.JSONField(default=dict)
    sql = models.TextField(blank=True)
    data_source = models.CharField(max_length=50)
    dataset_version = models.CharField(max_length=100, blank=True)


class AuthEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    email = models.EmailField(blank=True)
    event_type = models.CharField(max_length=50)
    event_status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
