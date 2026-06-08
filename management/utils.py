from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail

from .models import Notification


def admin_users():
    return User.objects.filter(is_superuser=True) | User.objects.filter(
        staff_profile__role="Admin"
    )


def notify_user(recipient, title, message, notification_type, project=None):
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        related_project=project,
    )


def notify_admins(title, message, notification_type, project=None):
    for user in admin_users().distinct():
        notify_user(user, title, message, notification_type, project)


def send_request_approved_email(project):
    if not project.client.email:
        return
    staff_name = project.assigned_staff.full_name if project.assigned_staff else "your assigned consultant"
    send_mail(
        "Your TK Research request has been approved",
        (
            f"Hello {project.client.full_name},\n\n"
            f"Your request '{project.title}' has been approved.\n"
            f"Service: {project.service}\n"
            f"Assigned staff: {staff_name}\n"
            f"Status: {project.status}\n"
            f"Quoted price: {project.quoted_price}\n\n"
            "Next steps: log in to your client portal to track progress and upload any supporting files."
        ),
        settings.DEFAULT_FROM_EMAIL,
        [project.client.email],
        fail_silently=True,
    )


def send_project_assigned_email(project):
    if not project.assigned_staff or not project.assigned_staff.user.email:
        return
    send_mail(
        "New project assigned to you",
        (
            f"Hello {project.assigned_staff.full_name},\n\n"
            f"You have been assigned to '{project.title}'.\n"
            f"Client: {project.client.full_name}\n"
            f"Service: {project.service}\n"
            f"Deadline: {project.deadline}\n\n"
            f"Description:\n{project.description}\n\n"
            "Open the staff portal to view the project."
        ),
        settings.DEFAULT_FROM_EMAIL,
        [project.assigned_staff.user.email],
        fail_silently=True,
    )


def send_request_rejected_email(project):
    if not project.client.email:
        return
    send_mail(
        "Update on your TK Research request",
        (
            f"Hello {project.client.full_name},\n\n"
            f"Your request '{project.title}' was not accepted or has been cancelled.\n"
            "Please contact TK Research if you need clarification."
        ),
        settings.DEFAULT_FROM_EMAIL,
        [project.client.email],
        fail_silently=True,
    )
