from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and not user.is_superuser:
            path = request.path
            allowed_prefixes = (
                reverse("change_password"),
                reverse("management:logout"),
                reverse("client:logout"),
                "/admin/",
                "/static/",
                "/media/",
            )
            if not path.startswith(allowed_prefixes) and self._must_change_password(user):
                return redirect("change_password")
        return self.get_response(request)

    def _must_change_password(self, user):
        client_profile = getattr(user, "client_profile", None)
        if client_profile and client_profile.must_change_password:
            return True
        staff_profile = getattr(user, "staff_profile", None)
        return bool(staff_profile and staff_profile.must_change_password)
