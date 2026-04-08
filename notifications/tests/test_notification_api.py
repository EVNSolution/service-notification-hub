from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from notifications.models import GeneralNotification, PushDeliveryLog, PushTokenRegistration


class NotificationApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin_account_id = str(uuid4())
        self.user_account_id = str(uuid4())
        self.other_account_id = str(uuid4())
        self.admin_token = self._issue_token("admin", self.admin_account_id)
        self.user_token = self._issue_token("user", self.user_account_id)
        self.other_user_token = self._issue_token("user", self.other_account_id)

    def _issue_token(self, role: str, account_id: str, *, allowed_nav_keys: list[str] | None = None) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": account_id,
            "email": f"{role}@example.com",
            "role": role,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "jti": str(uuid4()),
            "type": "access",
        }
        if allowed_nav_keys is not None:
            payload["allowed_nav_keys"] = allowed_nav_keys
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def _authenticate(self, token: str) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _create_token(
        self,
        *,
        account_id: str,
        device_key: str,
        is_active: bool = True,
        platform: str = PushTokenRegistration.Platform.ANDROID,
    ) -> PushTokenRegistration:
        return PushTokenRegistration.objects.create(
            account_id=account_id,
            channel=PushTokenRegistration.Channel.FCM,
            platform=platform,
            device_key=device_key,
            registration_token=f"token-{device_key}",
            is_active=is_active,
        )

    def _create_notification(
        self,
        *,
        recipient_account_id: str,
        status: str = GeneralNotification.Status.UNREAD,
        category: str = "general",
    ) -> GeneralNotification:
        kwargs = {
            "recipient_account_id": recipient_account_id,
            "category": category,
            "source_type": "manual",
            "source_ref": "seed",
            "title": "Seed Notification",
            "body": "Seed body",
            "status": status,
        }
        if status == GeneralNotification.Status.READ:
            kwargs["read_at"] = datetime(2026, 3, 29, tzinfo=timezone.utc)
        if status == GeneralNotification.Status.ARCHIVED:
            kwargs["archived_at"] = datetime(2026, 3, 29, tzinfo=timezone.utc)
        return GeneralNotification.objects.create(**kwargs)

    def test_unauthenticated_token_list_returns_401_shape(self) -> None:
        response = self.client.get("/fcm/tokens/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(set(response.data.keys()), {"code", "message", "details"})

    def test_user_can_register_and_list_own_tokens(self) -> None:
        self._create_token(account_id=self.other_account_id, device_key="other-device")
        self._authenticate(self.user_token)

        create_response = self.client.post(
            "/fcm/tokens/",
            {
                "channel": "fcm",
                "platform": "android",
                "device_key": "user-device",
                "registration_token": "user-token",
                "is_active": True,
                "app_version": "1.2.3",
            },
            format="json",
        )
        list_response = self.client.get("/fcm/tokens/")

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.data["account_id"], self.user_account_id)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["device_key"], "user-device")

    def test_admin_can_filter_tokens(self) -> None:
        self._create_token(account_id=self.user_account_id, device_key="device-a", platform=PushTokenRegistration.Platform.ANDROID)
        self._create_token(account_id=self.other_account_id, device_key="device-b", platform=PushTokenRegistration.Platform.IOS)
        self._authenticate(self.admin_token)

        response = self.client.get("/fcm/tokens/", {"platform": "ios"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["device_key"], "device-b")

    def test_admin_without_notifications_nav_key_is_denied(self) -> None:
        self._create_token(account_id=self.user_account_id, device_key="device-a")
        self._authenticate(self._issue_token("admin", self.admin_account_id, allowed_nav_keys=[]))

        response = self.client.get("/general/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["message"], "This API is not allowed by current navigation policy.")

    def test_user_can_read_and_mark_own_inbox_notification(self) -> None:
        own_notification = self._create_notification(recipient_account_id=self.user_account_id)
        self._create_notification(recipient_account_id=self.other_account_id)
        self._authenticate(self.user_token)

        list_response = self.client.get("/general/")
        patch_response = self.client.patch(
            f"/general/{own_notification.notification_id}/",
            {"status": "read"},
            format="json",
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.data["status"], "read")
        self.assertIsNotNone(patch_response.data["read_at"])

    def test_user_cannot_patch_inbox_fields_other_than_status(self) -> None:
        own_notification = self._create_notification(recipient_account_id=self.user_account_id)
        self._authenticate(self.user_token)

        response = self.client.patch(
            f"/general/{own_notification.notification_id}/",
            {"title": "Changed"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_non_admin_cannot_create_inbox_notification(self) -> None:
        self._authenticate(self.user_token)

        response = self.client.post(
            "/general/",
            {
                "recipient_account_id": self.other_account_id,
                "category": "announcement",
                "source_type": "announcement",
                "source_ref": "a-1",
                "title": "Hello",
                "body": "World",
                "status": "unread",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_notification_send_push_and_list_logs(self) -> None:
        self._create_token(account_id=self.user_account_id, device_key="device-a")
        self._authenticate(self.admin_token)

        create_inbox = self.client.post(
            "/general/",
            {
                "recipient_account_id": self.user_account_id,
                "category": "announcement",
                "source_type": "announcement",
                "source_ref": "a-1",
                "title": "Policy Updated",
                "body": "Check the latest policy.",
                "status": "unread",
            },
            format="json",
        )
        send_response = self.client.post(
            "/push-sends/",
            {
                "target_account_id": self.user_account_id,
                "event_type": "announcement",
                "category": "announcement",
                "source_type": "announcement",
                "source_ref": "a-1",
                "title": "Policy Updated",
                "body": "Check the latest policy.",
                "create_inbox": True,
            },
            format="json",
        )
        log_list = self.client.get("/push-logs/", {"delivery_status": "simulated_sent"})

        self.assertEqual(create_inbox.status_code, 201)
        self.assertEqual(send_response.status_code, 201)
        self.assertEqual(send_response.data["delivery_status"], "simulated_sent")
        self.assertIsNotNone(send_response.data["push_token_id"])
        self.assertIsNotNone(send_response.data["inbox_notification_id"])
        self.assertEqual(log_list.status_code, 200)
        self.assertEqual(len(log_list.data), 1)

    def test_send_without_active_token_creates_failed_log(self) -> None:
        self._authenticate(self.admin_token)

        response = self.client.post(
            "/push-sends/",
            {
                "target_account_id": self.other_account_id,
                "event_type": "support",
                "category": "support",
                "source_type": "support",
                "source_ref": "t-1",
                "title": "Support Updated",
                "body": "Support ticket updated.",
                "create_inbox": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["delivery_status"], "failed")
        self.assertEqual(response.data["failure_reason"], "active token not found.")
        self.assertEqual(PushDeliveryLog.objects.count(), 1)

    def test_admin_can_filter_inbox_and_logs(self) -> None:
        own_notification = self._create_notification(
            recipient_account_id=self.user_account_id,
            status=GeneralNotification.Status.ARCHIVED,
            category="support",
        )
        token = self._create_token(account_id=self.user_account_id, device_key="device-a")
        PushDeliveryLog.objects.create(
            target_account_id=self.user_account_id,
            push_token=token,
            channel=PushDeliveryLog.Channel.FCM,
            event_type="support",
            title="Support",
            body="Body",
            delivery_status=PushDeliveryLog.DeliveryStatus.SIMULATED_SENT,
            provider_message_id="simulated-1",
            inbox_notification=own_notification,
            requested_by_account_id=self.admin_account_id,
            delivered_at=datetime(2026, 3, 29, tzinfo=timezone.utc),
        )
        self._authenticate(self.admin_token)

        inbox_response = self.client.get("/general/", {"status": "archived", "recipient_account_id": self.user_account_id})
        log_response = self.client.get("/push-logs/", {"event_type": "support"})

        self.assertEqual(inbox_response.status_code, 200)
        self.assertEqual(len(inbox_response.data), 1)
        self.assertEqual(inbox_response.data[0]["notification_id"], str(own_notification.notification_id))
        self.assertEqual(log_response.status_code, 200)
        self.assertEqual(len(log_response.data), 1)
