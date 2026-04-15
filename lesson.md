Source: https://lessons.md

# service-notification-hub Lessons.md

Notification hub owns inbox and delivery-log runtime, but it does not prove external push delivery. A successful rollout here should not be described as FCM/provider cutover unless that provider path was verified separately.

The honest production smoke is `/api/notifications/health/ -> 200` plus `/api/notifications/general/ -> 401` without a token. That proves route, service startup, and auth protection without creating a real notification side effect.
