from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("setup/", views.setup, name="setup"),
    path("settings/", views.settings_view, name="settings"),
    path("backup/", views.backup_view, name="backup"),
    path("backup/create/", views.backup_create, name="backup_create"),
    path("backup/restore/", views.backup_restore, name="backup_restore"),
]
