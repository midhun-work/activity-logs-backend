from django.urls import path

from .views import ActivityLogDetailView, ActivityLogListView, ActivityLogMetaView

urlpatterns = [
    path("logs/", ActivityLogListView.as_view(), name="activity-logs"),
    path("logs/meta/", ActivityLogMetaView.as_view(), name="activity-logs-meta"),
    path("logs/<int:pk>/", ActivityLogDetailView.as_view(), name="activity-log-detail"),
]
