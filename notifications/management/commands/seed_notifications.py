from uuid import UUID

from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import GeneralNotification, PushDeliveryLog, PushTokenRegistration

ACTIVE_TOKEN_ID = UUID("94000000-0000-0000-0000-000000000001")
INACTIVE_TOKEN_ID = UUID("94000000-0000-0000-0000-000000000002")
UNREAD_NOTIFICATION_ID = UUID("94000000-0000-0000-0000-000000000101")
ARCHIVED_NOTIFICATION_ID = UUID("94000000-0000-0000-0000-000000000102")
SIMULATED_DELIVERY_LOG_ID = UUID("94000000-0000-0000-0000-000000000201")
SEED_RECIPIENT_ID = UUID("94000000-0000-0000-0000-000000000301")
SEED_REQUESTER_ID = UUID("94000000-0000-0000-0000-000000000302")


class Command(BaseCommand):
    help = "Seed deterministic notification hub bootstrap data."

    def handle(self, *args, **options):
        active_token, _ = PushTokenRegistration.objects.update_or_create(
            push_token_id=ACTIVE_TOKEN_ID,
            defaults={
                "account_id": SEED_RECIPIENT_ID,
                "channel": PushTokenRegistration.Channel.FCM,
                "platform": PushTokenRegistration.Platform.ANDROID,
                "device_key": "seed-android-01",
                "registration_token": "seed-token-active",
                "is_active": True,
                "app_version": "1.0.0",
            },
        )
        PushTokenRegistration.objects.update_or_create(
            push_token_id=INACTIVE_TOKEN_ID,
            defaults={
                "account_id": SEED_REQUESTER_ID,
                "channel": PushTokenRegistration.Channel.FCM,
                "platform": PushTokenRegistration.Platform.IOS,
                "device_key": "seed-ios-01",
                "registration_token": "seed-token-inactive",
                "is_active": False,
                "app_version": "1.0.0",
            },
        )

        unread_notification, _ = GeneralNotification.objects.update_or_create(
            notification_id=UNREAD_NOTIFICATION_ID,
            defaults={
                "recipient_account_id": SEED_RECIPIENT_ID,
                "category": "announcement",
                "source_type": "announcement",
                "source_ref": "92000000-0000-0000-0000-000000000001",
                "title": "Operator Policy Updated",
                "body": "Check the latest settlement policy update.",
                "status": GeneralNotification.Status.UNREAD,
                "read_at": None,
                "archived_at": None,
            },
        )
        GeneralNotification.objects.update_or_create(
            notification_id=ARCHIVED_NOTIFICATION_ID,
            defaults={
                "recipient_account_id": SEED_REQUESTER_ID,
                "category": "support",
                "source_type": "support",
                "source_ref": "93000000-0000-0000-0000-000000000001",
                "title": "Support Ticket Closed",
                "body": "Your ticket has been resolved.",
                "status": GeneralNotification.Status.ARCHIVED,
                "read_at": None,
                "archived_at": timezone.now(),
            },
        )

        PushDeliveryLog.objects.update_or_create(
            delivery_log_id=SIMULATED_DELIVERY_LOG_ID,
            defaults={
                "target_account_id": SEED_RECIPIENT_ID,
                "push_token": active_token,
                "channel": PushDeliveryLog.Channel.FCM,
                "event_type": "announcement",
                "title": "Operator Policy Updated",
                "body": "Check the latest settlement policy update.",
                "delivery_status": PushDeliveryLog.DeliveryStatus.SIMULATED_SENT,
                "provider_message_id": "simulated-seed-001",
                "failure_reason": "",
                "inbox_notification": unread_notification,
                "requested_by_account_id": SEED_REQUESTER_ID,
                "delivered_at": timezone.now(),
            },
        )

        self.stdout.write(self.style.SUCCESS("Seeded notification hub bootstrap data."))
