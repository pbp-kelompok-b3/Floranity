from django.urls import path

from . import views

app_name = "schedule"

urlpatterns = [
    path("jadwal/", views.calendar, name="calendar"),
    path("jadwal/sinkronisasi/", views.synchronize_schedule, name="synchronize"),
    path("jadwal/tindakan/", views.bulk_action, name="bulk_action"),
]
