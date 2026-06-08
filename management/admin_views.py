from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.contrib.auth.decorators import login_required

from .models import Client, Service, Project, Document, Payment, StaffProfile


@login_required
def admin_dashboard(request):
    total_clients = Client.objects.count()
    total_staff = StaffProfile.objects.filter(is_active=True).count()
    total_projects = Project.objects.count()
    completed_projects = Project.objects.filter(status="Completed").count()
    pending_projects = Project.objects.filter(status="Pending").count()
    in_progress_projects = Project.objects.filter(status="In Progress").count()

    total_revenue = Payment.objects.filter(status="Confirmed").aggregate(
        total=Sum("amount")
    )["total"] or 0

    if total_projects > 0:
        completion_rate = round((completed_projects / total_projects) * 100, 2)
    else:
        completion_rate = 0

    staff_performance = StaffProfile.objects.annotate(
        total_assigned=Count("assigned_projects"),
        completed=Count("assigned_projects", filter=Q(assigned_projects__status="Completed")),
        in_progress=Count("assigned_projects", filter=Q(assigned_projects__status="In Progress")),
        pending=Count("assigned_projects", filter=Q(assigned_projects__status="Pending")),
    )

    recent_projects = Project.objects.select_related(
        "client", "service", "assigned_staff"
    ).order_by("-created_at")[:10]

    context = {
        "total_clients": total_clients,
        "total_staff": total_staff,
        "total_projects": total_projects,
        "completed_projects": completed_projects,
        "pending_projects": pending_projects,
        "in_progress_projects": in_progress_projects,
        "completion_rate": completion_rate,
        "total_revenue": total_revenue,
        "staff_performance": staff_performance,
        "recent_projects": recent_projects,
    }

    return render(request, "admin_panel/dashboard.html", context)


@login_required
def admin_clients(request):
    clients = Client.objects.all().order_by("-created_at")

    return render(request, "admin_panel/clients.html", {
        "clients": clients
    })


@login_required
def admin_staff(request):
    staff_members = StaffProfile.objects.all().order_by("-created_at")

    return render(request, "admin_panel/staff.html", {
        "staff_members": staff_members
    })


@login_required
def admin_projects(request):
    projects = Project.objects.select_related(
        "client", "service", "assigned_staff"
    ).all().order_by("-created_at")

    return render(request, "admin_panel/projects.html", {
        "projects": projects
    })


@login_required
def project_detail(request, project_id):
    project = get_object_or_404(
        Project.objects.select_related("client", "service", "assigned_staff"),
        id=project_id
    )

    documents = project.documents.all().order_by("-uploaded_at")
    payments = project.payments.all().order_by("-payment_date")

    return render(request, "admin_panel/project_detail.html", {
        "project": project,
        "documents": documents,
        "payments": payments,
    })


@login_required
def assign_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    staff_members = StaffProfile.objects.filter(is_active=True)

    if request.method == "POST":
        staff_id = request.POST.get("assigned_staff")
        staff = get_object_or_404(StaffProfile, id=staff_id)

        project.assigned_staff = staff
        project.status = "In Progress"
        project.save()

        messages.success(request, "Project assigned successfully.")
        return redirect("project_detail", project_id=project.id)

    return render(request, "admin_panel/assign_project.html", {
        "project": project,
        "staff_members": staff_members,
    })


@login_required
def update_project_status(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.method == "POST":
        status = request.POST.get("status")
        payment_status = request.POST.get("payment_status")

        if status:
            project.status = status

        if payment_status:
            project.payment_status = payment_status

        project.save()
        messages.success(request, "Project updated successfully.")

    return redirect("project_detail", project_id=project.id)


@login_required
def admin_payments(request):
    payments = Payment.objects.select_related(
        "project", "project__client"
    ).all().order_by("-payment_date")

    total_confirmed = Payment.objects.filter(status="Confirmed").aggregate(
        total=Sum("amount")
    )["total"] or 0

    return render(request, "admin_panel/payments.html", {
        "payments": payments,
        "total_confirmed": total_confirmed,
    })


@login_required
def payment_detail(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related("project", "project__client"),
        id=payment_id
    )

    return render(request, "admin_panel/payment_detail.html", {
        "payment": payment
    })


@login_required
def admin_documents(request):
    documents = Document.objects.select_related(
        "project", "uploaded_by"
    ).all().order_by("-uploaded_at")

    return render(request, "admin_panel/documents.html", {
        "documents": documents
    })


@login_required
def create_staff(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        full_name = request.POST.get("full_name")
        phone = request.POST.get("phone")
        role = request.POST.get("role")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        StaffProfile.objects.create(
            user=user,
            full_name=full_name,
            phone=phone,
            role=role
        )

        messages.success(request, "Staff member created successfully.")
        return redirect("admin_staff")

    return render(request, "admin_panel/create_staff.html")


@login_required
def create_client(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        full_name = request.POST.get("full_name")
        phone = request.POST.get("phone")
        institution = request.POST.get("institution")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        Client.objects.create(
            user=user,
            full_name=full_name,
            phone=phone,
            email=email,
            institution=institution
        )

        messages.success(request, "Client created successfully.")
        return redirect("admin_clients")

    return render(request, "admin_panel/create_client.html")


@login_required
def admin_services(request):
    services = Service.objects.all().order_by("name")

    return render(request, "admin_panel/services.html", {
        "services": services
    })


@login_required
def create_service(request):
    if request.method == "POST":
        Service.objects.create(
            name=request.POST.get("name"),
            description=request.POST.get("description"),
            base_price=request.POST.get("base_price"),
            estimated_days=request.POST.get("estimated_days"),
            is_active=True if request.POST.get("is_active") == "on" else False
        )

        messages.success(request, "Service created successfully.")
        return redirect("admin_services")

    return render(request, "admin_panel/create_service.html")