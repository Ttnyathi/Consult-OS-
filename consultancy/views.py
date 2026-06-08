from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db import transaction

from .forms import ClientSignupForm
from management.models import Client, Notification, StaffProfile


def home(request):
    return render(request, "website/tk_research_consultancy.html")


def work(request):
    return render(request, "website/work.html")


def people(request):
    return render(request, "website/people.html")


def insights(request):
    return render(request, "website/insights.html")


def workflow(request):
    return render(request, "website/workflow.html")


def careers(request):
    return render(request, "website/careers.html")


def contact(request):
    return render(request, "website/contact.html")




def client_signup(request):
    if request.method == "POST":
        form = ClientSignupForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    full_name = form.cleaned_data["full_name"].strip()
                    email = form.cleaned_data["email"].lower().strip()
                    phone = form.cleaned_data.get("phone")
                    institution = form.cleaned_data.get("institution")
                    password = form.cleaned_data["password"]

                    name_parts = full_name.split()
                    first_name = name_parts[0] if name_parts else ""
                    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name
                    )

                    client = Client.objects.create(
                        user=user,
                        full_name=full_name,
                        phone=phone,
                        email=email,
                        institution=institution,
                        status="Limited",
                        must_change_password=False,
                    )

                    admins = StaffProfile.objects.filter(
                        role="Admin",
                        is_active=True
                    )

                    for admin in admins:
                        Notification.objects.create(
                            recipient=admin.user,
                            title="New Client Account Created",
                            message=f"{client.full_name} created a client account and now has limited access.",
                            notification_type="Account Created",
                            related_client=client
                        )

                login(request, user)

                messages.success(
                    request,
                    "Your account has been created. You currently have limited access."
                )

                return redirect("client:client_profile")

            except IntegrityError:
                form.add_error(None, "An account with these details already exists.")

            except Exception as e:
                form.add_error(None, f"Signup failed: {e}")

    else:
        form = ClientSignupForm()

    return render(request, "website/client_signup.html", {
        "form": form
    })