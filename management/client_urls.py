from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


app_name = "client"

urlpatterns = [
    path("", views.client_dashboard, name="client_home"),
    path("login/", views.management_login, name="client_login"),
    path("dashboard/", views.client_dashboard, name="client_dashboard"),
    path("projects/", views.client_projects, name="client_projects"),
    path("projects/<int:id>/", views.client_project_detail, name="client_project_detail"),
    path("projects/<int:id>/upload/", views.client_upload_document, name="client_upload_document"),
    path("requests/", views.client_requests, name="client_requests"),
    path("requests/new/", views.client_create_request, name="client_create_request"),
    path("requests/<int:id>/", views.client_request_detail, name="client_request_detail"),
    path("documents/", views.client_documents, name="client_documents"),
    path("payments/", views.client_payments, name="client_payments"),
    path("payments/<int:id>/", views.client_payment_detail, name="client_payment_detail"),
    path("notifications/", views.client_notifications, name="client_notifications"),
    path("notifications/<int:id>/read/", views.client_notification_read, name="client_notification_read"),
    path("profile/", views.client_profile, name="client_profile"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
]
