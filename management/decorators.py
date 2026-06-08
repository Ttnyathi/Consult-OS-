from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def is_admin_portal_user(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    staff_profile = getattr(user, "staff_profile", None)
    return bool(staff_profile and staff_profile.role == "Admin")


def is_staff_portal_user(user):
    if not user.is_authenticated:
        return False
    staff_profile = getattr(user, "staff_profile", None)
    return bool(staff_profile and staff_profile.is_active)


def admin_required(view_func):
    @wraps(view_func)
    @login_required(login_url="login")
    def wrapper(request, *args, **kwargs):
        if is_admin_portal_user(request.user):
            return view_func(request, *args, **kwargs)
        messages.error(request, "You do not have access to the admin portal.")
        return redirect("login")

    return wrapper


def client_required(view_func):
    @wraps(view_func)
    @login_required(login_url="login")
    def wrapper(request, *args, **kwargs):
        if hasattr(request.user, "client_profile"):
            return view_func(request, *args, **kwargs)
        messages.error(request, "You do not have access to the client portal.")
        return redirect("login")

    return wrapper


def staff_required(view_func):
    @wraps(view_func)
    @login_required(login_url="login")
    def wrapper(request, *args, **kwargs):
        if is_staff_portal_user(request.user):
            return view_func(request, *args, **kwargs)
        messages.error(request, "You do not have access to the staff portal.")
        return redirect("login")

    return wrapper
