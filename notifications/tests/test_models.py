from datetime import datetime, timezone
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.test import TestCase

from notifications.models import GeneralNotification, PushDeliveryLog, PushTokenRegistration


class NotificationModelTests(TestCase):
    def test_read_notification_requires_read_at(self) -> None:
        notification = GeneralNotification(
            recipient_account_id=uuid4(),
            category="general",
            source_type="manual",
            source_ref="seed",
            title="Read Me",
            body="Body",
            status=GeneralNotification.Status.READ,
        )

        with self.assertRaises(ValidationError):
            notification.full_clean()

    def test_archived_notification_requires_archived_at(self) -> None:
        notification = GeneralNotification(
            recipient_account_id=uuid4(),
            category="support",
            source_type="support",
            source_ref="ticket-1",
            title="Archived",
            body="Body",
            status=GeneralNotification.Status.ARCHIVED,
        )

        with self.assertRaises(ValidationError):
            notification.full_clean()

    def test_failed_delivery_log_requires_failure_reason(self) -> None:
        log = PushDeliveryLog(
            target_account_id=uuid4(),
            channel=PushDeliveryLog.Channel.FCM,
            event_type="support",
            title="Failure",
            body="Body",
            delivery_status=PushDeliveryLog.DeliveryStatus.FAILED,
            requested_by_account_id=uuid4(),
        )

        with self.assertRaises(ValidationError):
            log.full_clean()

    def test_simulated_sent_requires_delivered_at(self) -> None:
        log = PushDeliveryLog(
            target_account_id=uuid4(),
            channel=PushDeliveryLog.Channel.FCM,
            event_type="announcement",
            title="Sent",
            body="Body",
            delivery_status=PushDeliveryLog.DeliveryStatus.SIMULATED_SENT,
            provider_message_id="simulated-1",
            requested_by_account_id=uuid4(),
        )

        with self.assertRaises(ValidationError):
            log.full_clean()

    def test_token_registration_is_unique_per_account_and_device(self) -> None:
        account_id = uuid4()
        PushTokenRegistration.objects.create(
            account_id=account_id,
            channel=PushTokenRegistration.Channel.FCM,
            platform=PushTokenRegistration.Platform.ANDROID,
            device_key="device-1",
            registration_token="token-1",
        )
        duplicate = PushTokenRegistration(
            account_id=account_id,
            channel=PushTokenRegistration.Channel.FCM,
            platform=PushTokenRegistration.Platform.ANDROID,
            device_key="device-1",
            registration_token="token-2",
        )

        with self.assertRaises(ValidationError):
            duplicate.validate_constraints()

    def test_valid_records_pass_model_validation(self) -> None:
        token = PushTokenRegistration(
            account_id=uuid4(),
            channel=PushTokenRegistration.Channel.FCM,
            platform=PushTokenRegistration.Platform.WEB,
            device_key="browser-1",
            registration_token="token-3",
        )
        notification = GeneralNotification(
            recipient_account_id=uuid4(),
            category="general",
            source_type="manual",
            source_ref="seed",
            title="Ok",
            body="Body",
            status=GeneralNotification.Status.READ,
            read_at=datetime(2026, 3, 29, tzinfo=timezone.utc),
        )
        log = PushDeliveryLog(
            target_account_id=uuid4(),
            channel=PushDeliveryLog.Channel.FCM,
            event_type="general",
            title="Ok",
            body="Body",
            delivery_status=PushDeliveryLog.DeliveryStatus.SIMULATED_SENT,
            provider_message_id="simulated-ok",
            requested_by_account_id=uuid4(),
            delivered_at=datetime(2026, 3, 29, tzinfo=timezone.utc),
        )

        token.full_clean()
        notification.full_clean()
        log.full_clean()
