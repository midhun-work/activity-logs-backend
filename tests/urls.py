from django.urls import include, path

from tests.testapp import views

urlpatterns = [
    path("api/", include("activity_logs.urls")),
    path("notes/", views.create_note),
    path("notes/<int:pk>/", views.edit_note),
]
