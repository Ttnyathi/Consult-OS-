from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from management import views as management_views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", management_views.management_login, name="login"),
    path("change-password/", management_views.change_password, name="change_password"),
    path("panel/", include("management.urls")),
    path("client/", include("management.client_urls")),
    path("staff/", include("management.staff_urls")),
    path("", include("consultancy.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
