# service-notification-hub

## Purpose / Boundary

이 repo는 알림 채널 runtime 이다.

현재 역할:
- `PushTokenRegistration` CRUD
- `GeneralNotification` inbox read / create / read-state patch
- `PushDeliveryLog` 기록과 admin read API
- deterministic bootstrap seed command

포함하지 않음:
- announcement posting truth
- support ticket truth
- approval truth
- 실제 external FCM provider integration
- email / SMS channel
- 플랫폼 전체 compose와 gateway 설정

## Runtime Contract / Local Role

- compose service는 `notification-hub-api` 다.
- gateway prefix는 `/api/notifications/` 다.
- current API:
  - `/health/`
  - `/fcm/tokens/`
  - `/fcm/tokens/<push_token_id>/`
  - `/general/`
  - `/general/<notification_id>/`
  - `/push-sends/`
  - `/push-logs/`

## Local Run / Verification

- local run: `. .venv/bin/activate && python manage.py runserver 0.0.0.0:8000`
- local test: `. .venv/bin/activate && python manage.py test -v 2`

## Image Build / Deploy Contract

- prod contract is build, test, and immutable image publish only
- production runtime rollout ownership belongs to `runtime-prod-release`
- build and publish auth uses `ECR_BUILD_AWS_ROLE_ARN` plus shared `AWS_REGION`


- GitHub Actions workflow 이름은 `Build service-notification-hub image` 다.
- workflow는 immutable `service-notification-hub:<sha>` 이미지를 ECR로 publish 한다.
- runtime rollout은 `../runtime-prod-release/` 가 소유한다.
- production runtime shape와 canonical inventory는 `../runtime-prod-platform/` 이 소유한다.

## Environment Files And Safety Notes

- notification-hub proof를 external push provider integration proof로 과장하지 않는다.
- honest production proof는 `health 200 + protected 401` 조합으로 본다.

## Key Tests Or Verification Commands

- full Django tests: `. .venv/bin/activate && python manage.py test -v 2`
- honest smoke는 `/api/notifications/health/` 와 `/api/notifications/general/` protected path 조합이다.

## Root Docs / Runbooks

- `../../docs/boundaries/`
- `../../docs/mappings/`
- `../../docs/runbooks/ev-dashboard-ui-smoke-and-decommission.md`
- `../../docs/decisions/specs/2026-03-29-notification-hub-phase-1-activation-design.md`

## Root Development Whitelist

- 이 repo는 `clever-msa-platform` root `development/` whitelist에 포함된다.
- root visible set은 `front-web-console`, `edge-api-gateway`, `runtime-prod-release`, `runtime-prod-platform`, active `service-*` repo만 유지한다.
- local stack support repo, legacy infra repo, bridge lane repo는 root `development/` whitelist 바깥에서 관리한다.
- 이 README와 repo-local AGENTS는 운영 안내 문서이며 정본이 아니다. 경계, 계약, 런타임 truth는 root `docs/`를 따른다.
