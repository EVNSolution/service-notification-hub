from django.core.management import call_command
from django.test import TestCase

from notifications.models import GeneralNotification, PushDeliveryLog, PushTokenRegistration


class SeedNotificationsCommandTests(TestCase):
    def test_seed_notifications_creates_expected_records_idempotently(self) -> None:
        call_command("seed_notifications")

        self.assertEqual(PushTokenRegistration.objects.count(), 2)
        self.assertEqual(GeneralNotification.objects.count(), 2)
        self.assertEqual(PushDeliveryLog.objects.count(), 1)

        call_command("seed_notifications")

        self.assertEqual(PushTokenRegistration.objects.count(), 2)
        self.assertEqual(GeneralNotification.objects.count(), 2)
        self.assertEqual(PushDeliveryLog.objects.count(), 1)
