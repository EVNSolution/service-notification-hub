from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from notifications.models import GeneralNotification, PushDeliveryLog, PushTokenRegistration

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class PushTokenRegistrationSerializer(serializers.ModelSerializer):
    account_id = serializers.UUIDField(read_only=True)
    registered_at = serializers.DateTimeField(format=DATETIME_FORMAT, read_only=True)
    updated_at = serializers.DateTimeField(format=DATETIME_FORMAT, read_only=True)

    class Meta:
        model = PushTokenRegistration
        fields = (
            "push_token_id",
            "account_id",
            "channel",
            "platform",
            "device_key",
            "registration_token",
            "is_active",
            "app_version",
            "registered_at",
            "updated_at",
        )
        read_only_fields = ("push_token_id", "account_id", "registered_at", "updated_at")

    def validate(self, attrs):
        candidate = self.instance or PushTokenRegistration()
        for field, value in attrs.items():
            setattr(candidate, field, value)
        request = self.context.get("request")
        if request is not None and getattr(request.user, "account_id", None):
            candidate.account_id = request.user.account_id
        try:
            candidate.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs


class GeneralNotificationSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format=DATETIME_FORMAT, read_only=True)
    read_at = serializers.DateTimeField(format=DATETIME_FORMAT, read_only=True)
    archived_at = serializers.DateTimeField(format=DATETIME_FORMAT, read_only=True)

    class Meta:
        model = GeneralNotification
        fields = (
            "notification_id",
            "recipient_account_id",
            "category",
            "source_type",
            "source_ref",
            "title",
            "body",
            "status",
            "created_at",
            "read_at",
            "archived_at",
        )
        read_only_fields = ("notification_id", "created_at", "read_at", "archived_at")

    def validate(self, attrs):
        candidate = self.instance or GeneralNotification()
        for field, value in attrs.items():
            setattr(candidate, field, value)

        if candidate.status == GeneralNotification.Status.UNREAD:
            candidate.read_at = None
            candidate.archived_at = None
        elif candidate.status == GeneralNotification.Status.READ:
            candidate.read_at = candidate.read_at or timezone.now()
            candidate.archived_at = None
        elif candidate.status == GeneralNotification.Status.ARCHIVED:
            candidate.archived_at = candidate.archived_at or timezone.now()

        attrs["read_at"] = candidate.read_at
        attrs["archived_at"] = candidate.archived_at

        try:
            candidate.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs


class PushDeliveryLogSerializer(serializers.ModelSerializer):
    push_token_id = serializers.SerializerMethodField()
    inbox_notification_id = serializers.SerializerMethodField()
    requested_at = serializers.DateTimeField(format=DATETIME_FORMAT, read_only=True)
    delivered_at = serializers.DateTimeField(format=DATETIME_FORMAT, read_only=True)

    class Meta:
        model = PushDeliveryLog
        fields = (
            "delivery_log_id",
            "target_account_id",
            "push_token_id",
            "channel",
            "event_type",
            "title",
            "body",
            "delivery_status",
            "provider_message_id",
            "failure_reason",
            "inbox_notification_id",
            "requested_by_account_id",
            "requested_at",
            "delivered_at",
        )
        read_only_fields = fields

    def get_push_token_id(self, obj):
        return str(obj.push_token_id) if obj.push_token_id else None

    def get_inbox_notification_id(self, obj):
        return str(obj.inbox_notification_id) if obj.inbox_notification_id else None


class PushSendRequestSerializer(serializers.Serializer):
    target_account_id = serializers.UUIDField()
    push_token_id = serializers.UUIDField(required=False, allow_null=True)
    event_type = serializers.CharField(max_length=64)
    category = serializers.CharField(max_length=32, default="general")
    source_type = serializers.CharField(max_length=32, required=False, allow_blank=True)
    source_ref = serializers.CharField(max_length=128, required=False, allow_blank=True)
    title = serializers.CharField(max_length=200)
    body = serializers.CharField()
    create_inbox = serializers.BooleanField(default=True)


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
