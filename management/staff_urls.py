from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


app_name = "staff"

urlpatterns = [
    path("", views.staff_portal_dashboard, name="staff_home"),
    path("dashboard/", views.staff_portal_dashboard, name="staff_dashboard"),
    path("projects/", views.staff_portal_projects, name="staff_projects"),
    path("projects/<int:id>/", views.staff_portal_project_detail, name="staff_project_detail"),
    path("projects/<int:id>/documents/", views.staff_project_documents, name="staff_project_documents"),
    path("projects/<int:id>/upload/", views.staff_upload_document, name="staff_upload_document"),
    path("projects/<int:id>/progress/", views.staff_progress_update, name="staff_progress_update"),
    path("documents/", views.staff_portal_documents, name="staff_documents"),
    path("notifications/", views.staff_notifications, name="staff_notifications"),
    path("notifications/<int:id>/read/", views.staff_notification_read, name="staff_notification_read"),
    path("profile/", views.staff_portal_profile, name="staff_profile"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
]
