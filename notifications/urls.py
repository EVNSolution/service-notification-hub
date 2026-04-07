from django.urls import path

from notifications.views import (
    GeneralNotificationDetailView,
    GeneralNotificationListCreateView,
    HealthView,
    PushDeliveryLogListView,
    PushSendCreateView,
    PushTokenDetailView,
    PushTokenListCreateView,
)

urlpatterns = [
    path("health/", HealthView.as_view()),
    path("fcm/tokens/", PushTokenListCreateView.as_view()),
    path("fcm/tokens/<uuid:push_token_id>/", PushTokenDetailView.as_view()),
    path("general/", GeneralNotificationListCreateView.as_view()),
    path("general/<uuid:notification_id>/", GeneralNotificationDetailView.as_view()),
    path("push-sends/", PushSendCreateView.as_view()),
    path("push-logs/", PushDeliveryLogListView.as_view()),
]
