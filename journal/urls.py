from django.urls import path

from . import views

app_name = "journal"

urlpatterns = [
    path("journal/new/", views.journal_log_create, name="create"),
]
