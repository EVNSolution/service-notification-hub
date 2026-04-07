# service-notification-hub

이 repo는 알림 채널 runtime이다.

현재 역할:
- `PushTokenRegistration` CRUD
- `GeneralNotification` inbox read / create / read-state patch
- `PushDeliveryLog` 기록과 admin read API
- deterministic bootstrap seed command

이 repo는 절대 소유하지 않음:
- announcement posting truth
- support ticket truth
- approval truth
- 실제 external FCM provider integration
- email / SMS channel

현재 API:
- internal path: `/health/`
- internal path: `/fcm/tokens/`
- internal path: `/fcm/tokens/<push_token_id>/`
- internal path: `/general/`
- internal path: `/general/<notification_id>/`
- internal path: `/push-sends/`
- internal path: `/push-logs/`
- gateway prefix: `/api/notifications/`

아직 포함하지 않음:
- realtime fan-out
- batch retry scheduler
- webhook / websocket delivery
- external provider credential flow

현재 정본:
- `../../docs/mappings/`
- `../../docs/decisions/specs/2026-03-29-notification-hub-phase-1-activation-design.md`
