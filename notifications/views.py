from uuid import uuid4

from django.utils import timezone
from rest_framework import generics, mixins, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

try:
    from drf_spectacular.utils import extend_schema
except ModuleNotFoundError:
    def extend_schema(*args, **kwargs):
        def decorator(target):
            return target

        return decorator

from notifications.models import GeneralNotification, PushDeliveryLog, PushTokenRegistration
from notifications.permissions import AuthenticatedNotificationAccess, AdminOnlyAccess, is_admin
from notifications.serializers import (
    GeneralNotificationSerializer,
    HealthSerializer,
    PushDeliveryLogSerializer,
    PushSendRequestSerializer,
    PushTokenRegistrationSerializer,
)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: HealthSerializer})
    def get(self, request):
        return Response({"status": "ok"})


class PushTokenListCreateView(generics.ListCreateAPIView):
    serializer_class = PushTokenRegistrationSerializer
    permission_classes = [AuthenticatedNotificationAccess]

    def get_queryset(self):
        queryset = PushTokenRegistration.objects.all()
        user = self.request.user

        if not is_admin(user):
            queryset = queryset.filter(account_id=user.account_id)

        platform = self.request.query_params.get("platform")
        if platform:
            queryset = queryset.filter(platform=platform)

        channel = self.request.query_params.get("channel")
        if channel:
            queryset = queryset.filter(channel=channel)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        account_id = self.request.query_params.get("account_id")
        if account_id and is_admin(user):
            queryset = queryset.filter(account_id=account_id)

        return queryset

    def perform_create(self, serializer):
        serializer.save(account_id=self.request.user.account_id)


class PushTokenDetailView(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    generics.GenericAPIView,
):
    serializer_class = PushTokenRegistrationSerializer
    lookup_field = "push_token_id"
    permission_classes = [AuthenticatedNotificationAccess]
    http_method_names = ["get", "patch", "options", "head"]

    def get_queryset(self):
        queryset = PushTokenRegistration.objects.all()
        if is_admin(self.request.user):
            return queryset
        return queryset.filter(account_id=self.request.user.account_id)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class GeneralNotificationListCreateView(generics.ListCreateAPIView):
    serializer_class = GeneralNotificationSerializer
    permission_classes = [AuthenticatedNotificationAccess]

    def get_queryset(self):
        queryset = GeneralNotification.objects.all()
        user = self.request.user

        if not is_admin(user):
            queryset = queryset.filter(recipient_account_id=user.account_id)

        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)

        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)

        source_type = self.request.query_params.get("source_type")
        if source_type:
            queryset = queryset.filter(source_type=source_type)

        recipient_account_id = self.request.query_params.get("recipient_account_id")
        if recipient_account_id and is_admin(user):
            queryset = queryset.filter(recipient_account_id=recipient_account_id)

        return queryset

    def create(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("Admin role required.")
        return super().create(request, *args, **kwargs)


class GeneralNotificationDetailView(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    generics.GenericAPIView,
):
    serializer_class = GeneralNotificationSerializer
    lookup_field = "notification_id"
    permission_classes = [AuthenticatedNotificationAccess]
    http_method_names = ["get", "patch", "options", "head"]

    def get_queryset(self):
        queryset = GeneralNotification.objects.all()
        if is_admin(self.request.user):
            return queryset
        return queryset.filter(recipient_account_id=self.request.user.account_id)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        if not is_admin(request.user):
            allowed_fields = {"status"}
            if not set(request.data.keys()).issubset(allowed_fields):
                raise PermissionDenied("Only notification status can be updated.")
        return self.partial_update(request, *args, **kwargs)


class PushSendCreateView(APIView):
    permission_classes = [AdminOnlyAccess]

    @extend_schema(
        request=PushSendRequestSerializer,
        responses={201: PushDeliveryLogSerializer},
    )
    def post(self, request):
        serializer = PushSendRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_token = None
        explicit_push_token_id = data.get("push_token_id")
        if explicit_push_token_id:
            target_token = PushTokenRegistration.objects.filter(
                push_token_id=explicit_push_token_id,
                account_id=data["target_account_id"],
                is_active=True,
            ).first()
            if target_token is None:
                raise ValidationError({"push_token_id": ["active token not found for target account."]})
        else:
            target_token = PushTokenRegistration.objects.filter(
                account_id=data["target_account_id"],
                is_active=True,
            ).order_by("-updated_at").first()

        inbox_notification = None
        if data["create_inbox"]:
            inbox_notification = GeneralNotification.objects.create(
                recipient_account_id=data["target_account_id"],
                category=data["category"],
                source_type=data.get("source_type", ""),
                source_ref=data.get("source_ref", ""),
                title=data["title"],
                body=data["body"],
                status=GeneralNotification.Status.UNREAD,
            )

        if target_token is None:
            delivery_log = PushDeliveryLog.objects.create(
                target_account_id=data["target_account_id"],
                channel=PushDeliveryLog.Channel.FCM,
                event_type=data["event_type"],
                title=data["title"],
                body=data["body"],
                delivery_status=PushDeliveryLog.DeliveryStatus.FAILED,
                failure_reason="active token not found.",
                inbox_notification=inbox_notification,
                requested_by_account_id=request.user.account_id,
            )
        else:
            delivery_log = PushDeliveryLog.objects.create(
                target_account_id=data["target_account_id"],
                push_token=target_token,
                channel=PushDeliveryLog.Channel.FCM,
                event_type=data["event_type"],
                title=data["title"],
                body=data["body"],
                delivery_status=PushDeliveryLog.DeliveryStatus.SIMULATED_SENT,
                provider_message_id=f"simulated-{uuid4().hex[:12]}",
                inbox_notification=inbox_notification,
                requested_by_account_id=request.user.account_id,
                delivered_at=timezone.now(),
            )

        return Response(PushDeliveryLogSerializer(delivery_log).data, status=status.HTTP_201_CREATED)


class PushDeliveryLogListView(generics.ListAPIView):
    serializer_class = PushDeliveryLogSerializer
    permission_classes = [AdminOnlyAccess]

    def get_queryset(self):
        queryset = PushDeliveryLog.objects.select_related("push_token", "inbox_notification").all()

        delivery_status = self.request.query_params.get("delivery_status")
        if delivery_status:
            queryset = queryset.filter(delivery_status=delivery_status)

        event_type = self.request.query_params.get("event_type")
        if event_type:
            queryset = queryset.filter(event_type=event_type)

        target_account_id = self.request.query_params.get("target_account_id")
        if target_account_id:
            queryset = queryset.filter(target_account_id=target_account_id)

        return queryset
