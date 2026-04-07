import uuid

from django.core.exceptions import ValidationError
from django.db import models


class PushTokenRegistration(models.Model):
    class Channel(models.TextChoices):
        FCM = "fcm", "fcm"

    class Platform(models.TextChoices):
        ANDROID = "android", "android"
        IOS = "ios", "ios"
        WEB = "web", "web"

    push_token_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account_id = models.UUIDField(db_index=True)
    channel = models.CharField(max_length=16, choices=Channel.choices, default=Channel.FCM)
    platform = models.CharField(max_length=16, choices=Platform.choices)
    device_key = models.CharField(max_length=64)
    registration_token = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    app_version = models.CharField(max_length=32, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "push_token_id")
        constraints = [
            models.UniqueConstraint(
                fields=("account_id", "device_key"),
                name="uniq_notification_token_account_device",
            )
        ]


class GeneralNotification(models.Model):
    class Status(models.TextChoices):
        UNREAD = "unread", "unread"
        READ = "read", "read"
        ARCHIVED = "archived", "archived"

    notification_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient_account_id = models.UUIDField(db_index=True)
    category = models.CharField(max_length=32)
    source_type = models.CharField(max_length=32, blank=True)
    source_ref = models.CharField(max_length=128, blank=True)
    title = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.UNREAD)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at", "notification_id")

    def clean(self):
        errors = {}
        if self.status == self.Status.UNREAD:
            if self.read_at is not None:
                errors["read_at"] = ["unread notification cannot have read_at."]
            if self.archived_at is not None:
                errors["archived_at"] = ["unread notification cannot have archived_at."]
        if self.status == self.Status.READ:
            if self.read_at is None:
                errors["read_at"] = ["read notification requires read_at."]
            if self.archived_at is not None:
                errors["archived_at"] = ["read notification cannot have archived_at."]
        if self.status == self.Status.ARCHIVED and self.archived_at is None:
            errors["archived_at"] = ["archived notification requires archived_at."]
        if errors:
            raise ValidationError(errors)


class PushDeliveryLog(models.Model):
    class Channel(models.TextChoices):
        FCM = "fcm", "fcm"

    class DeliveryStatus(models.TextChoices):
        SIMULATED_SENT = "simulated_sent", "simulated_sent"
        FAILED = "failed", "failed"

    delivery_log_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_account_id = models.UUIDField(db_index=True)
    push_token = models.ForeignKey(
        PushTokenRegistration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_logs",
    )
    channel = models.CharField(max_length=16, choices=Channel.choices, default=Channel.FCM)
    event_type = models.CharField(max_length=64)
    title = models.CharField(max_length=200)
    body = models.TextField()
    delivery_status = models.CharField(max_length=32, choices=DeliveryStatus.choices)
    provider_message_id = models.CharField(max_length=128, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    inbox_notification = models.ForeignKey(
        GeneralNotification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_logs",
    )
    requested_by_account_id = models.UUIDField()
    requested_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-requested_at", "delivery_log_id")

    def clean(self):
        errors = {}
        if self.delivery_status == self.DeliveryStatus.SIMULATED_SENT and self.delivered_at is None:
            errors["delivered_at"] = ["simulated sent log requires delivered_at."]
        if self.delivery_status == self.DeliveryStatus.FAILED and not self.failure_reason:
            errors["failure_reason"] = ["failed log requires failure_reason."]
        if errors:
            raise ValidationError(errors)
