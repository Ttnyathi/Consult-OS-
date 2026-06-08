import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import admin_required, is_admin_portal_user
from .forms import (
    AssignProjectForm,
    ClientCreateForm,
    ClientDocumentUploadForm,
    ClientForm,
    ClientProfileForm,
    ClientRequestForm,
    DocumentForm,
    PaymentForm,
    ProgressUpdateForm,
    ProjectForm,
    ProjectStatusForm,
    RequestApprovalForm,
    ServiceForm,
    StaffCreateForm,
    StaffDocumentUploadForm,
    StaffProfileForm,
    generate_temporary_password,
)
from .models import Client, Document, Notification, Payment, Project, Service, StaffProfile
from .utils import (
    notify_admins,
    notify_user,
    send_project_assigned_email,
    send_request_approved_email,
    send_request_rejected_email,
)


ACTIVE_PROJECT_STATUSES = ["Pending", "Quoted", "In Progress", "Under Review"]


def paginate(request, queryset, per_page=20):
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


def money(value):
    return value or Decimal("0.00")


def project_amount_paid(project):
    return money(project.payments.filter(status="Confirmed").aggregate(total=Sum("amount"))["total"])


def project_balance(project):
    quoted = project.quoted_price or Decimal("0.00")
    return quoted - project_amount_paid(project)


def sync_project_payment_status(project):
    quoted = project.quoted_price or Decimal("0.00")
    paid = project_amount_paid(project)
    if paid <= 0:
        status = "Unpaid"
    elif quoted and paid >= quoted:
        status = "Fully Paid"
    else:
        status = "Deposit Paid"
    if project.payment_status != status:
        project.payment_status = status
        project.save(update_fields=["payment_status", "updated_at"])


def workload_status(active_count):
    if active_count <= 2:
        return "Low"
    if active_count <= 5:
        return "Balanced"
    return "Heavy"


def staff_stats_queryset():
    return StaffProfile.objects.select_related("user").annotate(
        total_assigned=Count("assigned_projects"),
        completed_count=Count(
            "assigned_projects",
            filter=Q(assigned_projects__status="Completed"),
        ),
        active_count=Count(
            "assigned_projects",
            filter=Q(assigned_projects__status__in=ACTIVE_PROJECT_STATUSES),
        ),
        overdue_count=Count(
            "assigned_projects",
            filter=Q(
                assigned_projects__deadline__lt=timezone.localdate(),
                assigned_projects__status__in=ACTIVE_PROJECT_STATUSES,
            ),
        ),
    )


def management_login(request):
    if request.user.is_authenticated:
        if is_admin_portal_user(request.user):
            return redirect("management:admin_dashboard")
        if hasattr(request.user, "staff_profile"):
            return redirect("staff:staff_dashboard")
        if hasattr(request.user, "client_profile"):
            return redirect("client:client_dashboard")
        return render(
            request,
            "admin_panel/login.html",
            {"form": AuthenticationForm(request), "no_access": True},
        )

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if is_admin_portal_user(user):
                login(request, user)
                return redirect(request.POST.get("next") or "management:admin_dashboard")
            if hasattr(user, "staff_profile"):
                login(request, user)
                return redirect(request.POST.get("next") or "staff:staff_dashboard")
            if hasattr(user, "client_profile"):
                login(request, user)
                return redirect(request.POST.get("next") or "client:client_dashboard")
            return render(
                request,
                "admin_panel/login.html",
                {"form": form, "no_access": True},
            )
    else:
        form = AuthenticationForm(request)
    return render(request, "admin_panel/login.html", {"form": form})


@login_required(login_url="login")
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            client_profile = getattr(user, "client_profile", None)
            if client_profile:
                client_profile.must_change_password = False
                client_profile.save(update_fields=["must_change_password"])
            staff_profile = getattr(user, "staff_profile", None)
            if staff_profile:
                staff_profile.must_change_password = False
                staff_profile.save(update_fields=["must_change_password"])
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been changed.")
            if is_admin_portal_user(user):
                return redirect("management:admin_dashboard")
            if hasattr(user, "staff_profile"):
                return redirect("staff:staff_dashboard")
            if hasattr(user, "client_profile"):
                return redirect("client:client_dashboard")
            return redirect("/")
    else:
        form = PasswordChangeForm(request.user)
    template = "client_panel/change_password.html" if hasattr(request.user, "client_profile") else "admin_panel/change_password.html"
    return render(request, template, {"form": form})


@admin_required
def admin_dashboard(request):
    today = timezone.localdate()
    urgent_until = today + timezone.timedelta(days=7)
    total_projects = Project.objects.count()
    completed_projects = Project.objects.filter(status="Completed").count()
    completion_rate = round((completed_projects / total_projects) * 100, 1) if total_projects else 0
    staff_workload = []
    for member in staff_stats_queryset().order_by("full_name"):
        rate = round((member.completed_count / member.total_assigned) * 100, 1) if member.total_assigned else 0
        staff_workload.append({"member": member, "completion_rate": rate, "workload_status": workload_status(member.active_count)})

    context = {
        "total_clients": Client.objects.count(),
        "total_staff": StaffProfile.objects.count(),
        "total_projects": total_projects,
        "pending_projects": Project.objects.filter(status="Pending").count(),
        "quoted_projects": Project.objects.filter(status="Quoted").count(),
        "in_progress_projects": Project.objects.filter(status="In Progress").count(),
        "under_review_projects": Project.objects.filter(status="Under Review").count(),
        "completed_projects": completed_projects,
        "cancelled_projects": Project.objects.filter(status="Cancelled").count(),
        "completion_rate": completion_rate,
        "total_confirmed_revenue": money(Payment.objects.filter(status="Confirmed").aggregate(total=Sum("amount"))["total"]),
        "new_request_count": Project.objects.filter(requested_by_client=True, status="Pending").count(),
        "recent_projects": Project.objects.select_related("client", "service", "assigned_staff").order_by("-created_at")[:8],
        "recent_clients": Client.objects.order_by("-created_at")[:6],
        "recent_payments": Payment.objects.select_related("project", "project__client").order_by("-created_at")[:6],
        "staff_workload": staff_workload,
        "upcoming_deadlines": Project.objects.select_related("client", "assigned_staff").filter(deadline__gte=today, deadline__lte=urgent_until).exclude(status__in=["Completed", "Cancelled"]).order_by("deadline")[:8],
    }
    return render(request, "admin_panel/dashboard.html", context)


@admin_required
def admin_clients(request):
    query = request.GET.get("q", "").strip()
    clients = Client.objects.select_related("user").order_by("full_name")
    if query:
        clients = clients.filter(Q(full_name__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query) | Q(institution__icontains=query))
    return render(request, "admin_panel/clients.html", {"clients": paginate(request, clients), "query": query})


@admin_required
def client_detail(request, id):
    client = get_object_or_404(Client.objects.select_related("user"), id=id)
    projects = client.projects.select_related("service", "assigned_staff").order_by("-created_at")
    payments = Payment.objects.select_related("project").filter(project__client=client).order_by("-payment_date")
    documents = Document.objects.select_related("project", "uploaded_by").filter(project__client=client).order_by("-uploaded_at")
    total_paid = money(payments.filter(status="Confirmed").aggregate(total=Sum("amount"))["total"])
    quoted_total = money(projects.aggregate(total=Sum("quoted_price"))["total"])
    return render(request, "admin_panel/client_detail.html", {"client": client, "projects": projects, "payments": payments, "documents": documents, "total_paid": total_paid, "outstanding_balance": quoted_total - total_paid})


@admin_required
def create_client(request):
    form = ClientCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        client = form.save()
        messages.success(
            request,
            "Client account created successfully. Temporary password: "
            f"{form.temporary_password}. User will be required to change password on first login.",
        )
        return redirect("management:client_detail", id=client.id)
    return render(request, "admin_panel/create_client.html", {"form": form, "title": "Create client"})


@admin_required
def edit_client(request, id):
    client = get_object_or_404(Client, id=id)
    form = ClientForm(request.POST or None, instance=client)
    if request.method == "POST" and form.is_valid():
        client = form.save()
        client.user.email = client.email
        client.user.save(update_fields=["email"])
        messages.success(request, "Client updated.")
        return redirect("management:client_detail", id=client.id)
    return render(request, "admin_panel/create_client.html", {"form": form, "title": "Edit client"})


@admin_required
def delete_client(request, id):
    client = get_object_or_404(Client, id=id)
    if client.projects.exists():
        messages.error(request, "Client cannot be deleted while projects exist.")
    else:
        client.user.delete()
        messages.success(request, "Client deleted.")
    return redirect("management:admin_clients")


@admin_required
def reset_client_password(request, id):
    client = get_object_or_404(Client.objects.select_related("user"), id=id)
    temporary_password = generate_temporary_password()
    client.user.set_password(temporary_password)
    client.user.save(update_fields=["password"])
    client.must_change_password = True
    client.save(update_fields=["must_change_password"])
    messages.success(
        request,
        "Client password reset. Temporary password: "
        f"{temporary_password}. User will be required to change password on next login.",
    )
    return redirect("management:client_detail", id=client.id)


@admin_required
def admin_staff(request):
    role = request.GET.get("role", "")
    staff = staff_stats_queryset().order_by("full_name")
    if role:
        staff = staff.filter(role=role)
    rows = []
    for member in staff:
        rate = round((member.completed_count / member.total_assigned) * 100, 1) if member.total_assigned else 0
        rows.append({"member": member, "completion_rate": rate, "workload_status": workload_status(member.active_count)})
    return render(request, "admin_panel/staff.html", {"staff_rows": rows, "roles": StaffProfile.ROLE_CHOICES, "selected_role": role})


@admin_required
def staff_detail(request, id):
    staff = get_object_or_404(staff_stats_queryset(), id=id)
    assigned_projects = staff.assigned_projects.select_related("client", "service").order_by("deadline")
    completion_rate = round((staff.completed_count / staff.total_assigned) * 100, 1) if staff.total_assigned else 0
    return render(request, "admin_panel/staff_detail.html", {"staff": staff, "assigned_projects": assigned_projects, "completion_rate": completion_rate, "workload_status": workload_status(staff.active_count)})


@admin_required
def create_staff(request):
    form = StaffCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        staff = form.save()
        messages.success(
            request,
            "Staff account created successfully. Temporary password: "
            f"{form.temporary_password}. User will be required to change password on first login.",
        )
        return redirect("management:staff_detail", id=staff.id)
    return render(request, "admin_panel/create_staff.html", {"form": form, "title": "Create staff"})


@admin_required
def edit_staff(request, id):
    staff = get_object_or_404(StaffProfile, id=id)
    form = StaffProfileForm(request.POST or None, instance=staff)
    if request.method == "POST" and form.is_valid():
        staff = form.save()
        staff.user.is_staff = staff.role == "Admin"
        staff.user.save(update_fields=["is_staff"])
        messages.success(request, "Staff profile updated.")
        return redirect("management:staff_detail", id=staff.id)
    return render(request, "admin_panel/create_staff.html", {"form": form, "title": "Edit staff"})


@admin_required
def toggle_staff(request, id):
    staff = get_object_or_404(StaffProfile, id=id)
    staff.is_active = not staff.is_active
    staff.save(update_fields=["is_active"])
    messages.success(request, "Staff status updated.")
    return redirect("management:admin_staff")


@admin_required
def reset_staff_password(request, id):
    staff = get_object_or_404(StaffProfile.objects.select_related("user"), id=id)
    temporary_password = generate_temporary_password()
    staff.user.set_password(temporary_password)
    staff.user.save(update_fields=["password"])
    staff.must_change_password = True
    staff.save(update_fields=["must_change_password"])
    messages.success(
        request,
        "Staff password reset. Temporary password: "
        f"{temporary_password}. User will be required to change password on next login.",
    )
    return redirect("management:staff_detail", id=staff.id)


@admin_required
def admin_services(request):
    services = Service.objects.annotate(project_count=Count("projects"), revenue=Sum("projects__payments__amount", filter=Q(projects__payments__status="Confirmed"))).order_by("name")
    return render(request, "admin_panel/services.html", {"services": services})


@admin_required
def create_service(request):
    form = ServiceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Service created.")
        return redirect("management:admin_services")
    return render(request, "admin_panel/service_form.html", {"form": form, "title": "Create service"})


@admin_required
def edit_service(request, id):
    service = get_object_or_404(Service, id=id)
    form = ServiceForm(request.POST or None, instance=service)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Service updated.")
        return redirect("management:admin_services")
    return render(request, "admin_panel/service_form.html", {"form": form, "title": "Edit service"})


@admin_required
def toggle_service(request, id):
    service = get_object_or_404(Service, id=id)
    service.is_active = not service.is_active
    service.save(update_fields=["is_active"])
    messages.success(request, "Service status updated.")
    return redirect("management:admin_services")


@admin_required
def delete_service(request, id):
    service = get_object_or_404(Service, id=id)
    if service.projects.exists():
        messages.error(request, "Service cannot be deleted while projects depend on it.")
    else:
        service.delete()
        messages.success(request, "Service deleted.")
    return redirect("management:admin_services")


@admin_required
def admin_projects(request):
    projects = Project.objects.select_related("client", "service", "assigned_staff").order_by("-created_at")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    payment_status = request.GET.get("payment_status", "")
    staff_id = request.GET.get("staff", "")
    service_id = request.GET.get("service", "")
    if query:
        projects = projects.filter(Q(title__icontains=query) | Q(client__full_name__icontains=query) | Q(client__institution__icontains=query))
    if status:
        projects = projects.filter(status=status)
    if payment_status:
        projects = projects.filter(payment_status=payment_status)
    if staff_id:
        projects = projects.filter(assigned_staff_id=staff_id)
    if service_id:
        projects = projects.filter(service_id=service_id)
    context = {"projects": paginate(request, projects), "query": query, "status": status, "payment_status": payment_status, "staff_id": staff_id, "service_id": service_id, "staff": StaffProfile.objects.filter(is_active=True), "services": Service.objects.filter(is_active=True), "status_choices": Project.STATUS_CHOICES, "payment_status_choices": Project.PAYMENT_STATUS_CHOICES}
    return render(request, "admin_panel/projects.html", context)


@admin_required
def create_project(request):
    form = ProjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        project = form.save()
        messages.success(request, "Project created.")
        return redirect("management:project_detail", id=project.id)
    return render(request, "admin_panel/project_form.html", {"form": form, "title": "Create project"})


@admin_required
def edit_project(request, id):
    project = get_object_or_404(Project, id=id)
    form = ProjectForm(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid():
        project = form.save()
        sync_project_payment_status(project)
        messages.success(request, "Project updated.")
        return redirect("management:project_detail", id=project.id)
    return render(request, "admin_panel/project_form.html", {"form": form, "title": "Edit project"})


@admin_required
def project_detail(request, id):
    project = get_object_or_404(Project.objects.select_related("client", "service", "assigned_staff"), id=id)
    documents = project.documents.select_related("uploaded_by").order_by("-uploaded_at")
    payments = project.payments.order_by("-payment_date")
    progress_updates = project.progress_updates.select_related("updated_by")
    amount_paid = project_amount_paid(project)
    balance_due = project_balance(project)
    activity = [
        {"label": "Project created", "date": project.created_at},
        {"label": "Last updated", "date": project.updated_at},
    ]
    return render(request, "admin_panel/project_detail.html", {"project": project, "documents": documents, "payments": payments, "progress_updates": progress_updates, "status_form": ProjectStatusForm(instance=project), "amount_paid": amount_paid, "balance_due": balance_due, "activity": activity})


@admin_required
def assign_project(request, id):
    project = get_object_or_404(Project, id=id)
    form = AssignProjectForm(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid():
        project = form.save(commit=False)
        if form.cleaned_data["move_to_in_progress"] and project.status in ["Pending", "Quoted"]:
            project.status = "In Progress"
        project.save()
        if project.assigned_staff:
            notify_user(project.assigned_staff.user, "Project assigned", f"You have been assigned to {project.title}.", "Project Assigned", project)
            notify_user(project.client.user, "Project assigned", f"{project.title} has been assigned to {project.assigned_staff.full_name}.", "Project Assigned", project)
        messages.success(request, "Project assignment updated.")
        return redirect("management:project_detail", id=project.id)
    return render(request, "admin_panel/assign_project.html", {"project": project, "form": form})


@admin_required
def update_project_status(request, id):
    project = get_object_or_404(Project, id=id)
    form = ProjectStatusForm(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid():
        form.save()
        notify_user(project.client.user, "Project status updated", f"{project.title} is now {project.status}.", "Project Updated", project)
        if project.assigned_staff:
            notify_user(project.assigned_staff.user, "Project status updated", f"{project.title} is now {project.status}.", "Project Updated", project)
        messages.success(request, "Project status updated.")
    return redirect("management:project_detail", id=project.id)


@admin_required
def admin_documents(request):
    documents = Document.objects.select_related("project", "uploaded_by").order_by("-uploaded_at")
    doc_type = request.GET.get("type", "")
    project_id = request.GET.get("project", "")
    uploaded_by = request.GET.get("uploaded_by", "")
    if doc_type:
        documents = documents.filter(document_type=doc_type)
    if project_id:
        documents = documents.filter(project_id=project_id)
    if uploaded_by:
        documents = documents.filter(uploaded_by_id=uploaded_by)
    return render(request, "admin_panel/documents.html", {"documents": paginate(request, documents), "document_types": Document.DOCUMENT_TYPE_CHOICES, "projects": Project.objects.order_by("title"), "uploaders": Document.objects.exclude(uploaded_by=None).values_list("uploaded_by_id", "uploaded_by__username").distinct(), "doc_type": doc_type, "project_id": project_id, "uploaded_by": uploaded_by})


@admin_required
def create_document(request, id=None):
    initial_project = id or request.GET.get("project")
    form = DocumentForm(
        request.POST or None,
        request.FILES or None,
        initial={"project": initial_project},
    )
    if request.method == "POST" and form.is_valid():
        document = form.save(commit=False)
        document.uploaded_by = request.user
        document.save()
        messages.success(request, "Document uploaded.")
        return redirect("management:project_detail", id=document.project_id)
    return render(request, "admin_panel/document_form.html", {"form": form, "title": "Upload document"})


@admin_required
def delete_document(request, id):
    document = get_object_or_404(Document, id=id)
    project_id = document.project_id
    document.delete()
    messages.success(request, "Document deleted.")
    next_url = request.GET.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("management:project_detail", id=project_id)


@admin_required
def admin_payments(request):
    payments = Payment.objects.select_related("project", "project__client").order_by("-payment_date")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    method = request.GET.get("method", "")
    if query:
        payments = payments.filter(Q(reference__icontains=query) | Q(project__title__icontains=query) | Q(project__client__full_name__icontains=query))
    if status:
        payments = payments.filter(status=status)
    if method:
        payments = payments.filter(payment_method=method)
    total_confirmed_revenue = money(payments.filter(status="Confirmed").aggregate(total=Sum("amount"))["total"])
    current_month = timezone.localdate().replace(day=1)
    monthly_revenue = money(Payment.objects.filter(status="Confirmed", payment_date__gte=current_month).aggregate(total=Sum("amount"))["total"])
    outstanding = sum(project_balance(project) for project in Project.objects.prefetch_related("payments").exclude(payment_status="Fully Paid"))
    return render(request, "admin_panel/payments.html", {"payments": paginate(request, payments), "total_confirmed_revenue": total_confirmed_revenue, "monthly_revenue": monthly_revenue, "outstanding_balance": outstanding, "payment_statuses": Payment.PAYMENT_STATUS_CHOICES, "payment_methods": Payment.PAYMENT_METHOD_CHOICES, "query": query, "status": status, "method": method})


@admin_required
def create_payment(request, id=None):
    form = PaymentForm(request.POST or None, initial={"project": id or request.GET.get("project")})
    if request.method == "POST" and form.is_valid():
        payment = form.save()
        sync_project_payment_status(payment.project)
        if payment.status == "Confirmed":
            notify_user(payment.project.client.user, "Payment confirmed", f"Payment of {payment.amount} for {payment.project.title} was confirmed.", "Payment Updated", payment.project)
        messages.success(request, "Payment recorded.")
        return redirect("management:payment_detail", id=payment.id)
    return render(request, "admin_panel/payment_form.html", {"form": form, "title": "Record payment"})


@admin_required
def edit_payment(request, id):
    payment = get_object_or_404(Payment, id=id)
    form = PaymentForm(request.POST or None, instance=payment)
    if request.method == "POST" and form.is_valid():
        payment = form.save()
        sync_project_payment_status(payment.project)
        if payment.status == "Confirmed":
            notify_user(payment.project.client.user, "Payment confirmed", f"Payment of {payment.amount} for {payment.project.title} was confirmed.", "Payment Updated", payment.project)
        messages.success(request, "Payment updated.")
        return redirect("management:payment_detail", id=payment.id)
    return render(request, "admin_panel/payment_form.html", {"form": form, "title": "Edit payment"})


@admin_required
def payment_detail(request, id):
    payment = get_object_or_404(Payment.objects.select_related("project", "project__client", "project__service"), id=id)
    return render(request, "admin_panel/payment_detail.html", {"payment": payment, "company_name": "TK Research"})


@admin_required
def admin_assignments(request):
    role = request.GET.get("role", "")
    status = request.GET.get("workload", "")
    rows = []
    staff = staff_stats_queryset().order_by("full_name")
    if role:
        staff = staff.filter(role=role)
    for member in staff:
        workload = workload_status(member.active_count)
        if status and workload != status:
            continue
        rows.append({"member": member, "workload_status": workload, "projects": member.assigned_projects.select_related("client", "service").filter(status__in=ACTIVE_PROJECT_STATUSES).order_by("deadline")})
    return render(request, "admin_panel/assignments.html", {"rows": rows, "roles": StaffProfile.ROLE_CHOICES, "selected_role": role, "selected_workload": status, "workload_choices": ["Low", "Balanced", "Heavy"]})


@admin_required
def admin_reports(request):
    total_projects = Project.objects.count()
    completed = Project.objects.filter(status="Completed").count()
    current_month = timezone.localdate().replace(day=1)
    context = {
        "completion_rate": round((completed / total_projects) * 100, 1) if total_projects else 0,
        "revenue_total": money(Payment.objects.filter(status="Confirmed").aggregate(total=Sum("amount"))["total"]),
        "revenue_month": money(Payment.objects.filter(status="Confirmed", payment_date__gte=current_month).aggregate(total=Sum("amount"))["total"]),
        "projects_by_status": Project.objects.values("status").annotate(total=Count("id")).order_by("status"),
        "projects_by_service": Service.objects.annotate(total_projects=Count("projects")).order_by("name"),
        "staff_performance": staff_stats_queryset().order_by("full_name"),
        "clients_this_month": Client.objects.filter(created_at__date__gte=current_month).count(),
        "overdue_projects": Project.objects.filter(deadline__lt=timezone.localdate(), status__in=ACTIVE_PROJECT_STATUSES),
        "unpaid_projects": Project.objects.filter(payment_status="Unpaid"),
        "fully_paid_projects": Project.objects.filter(payment_status="Fully Paid"),
    }
    return render(request, "admin_panel/reports.html", context)


@admin_required
def export_projects_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="projects.csv"'
    writer = csv.writer(response)
    writer.writerow(["Title", "Client", "Service", "Status", "Payment Status", "Deadline"])
    for project in Project.objects.select_related("client", "service").order_by("title"):
        writer.writerow([project.title, project.client.full_name, project.service or "", project.status, project.payment_status, project.deadline])
    return response


@admin_required
def export_payments_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="payments.csv"'
    writer = csv.writer(response)
    writer.writerow(["Project", "Client", "Amount", "Method", "Status", "Date", "Reference"])
    for payment in Payment.objects.select_related("project", "project__client").order_by("-payment_date"):
        writer.writerow([payment.project.title, payment.project.client.full_name, payment.amount, payment.payment_method, payment.status, payment.payment_date, payment.reference or ""])
    return response


@admin_required
def admin_settings(request):
    return render(request, "admin_panel/settings.html", {"company_name": "TK Research", "admin_user": request.user})


@admin_required
def admin_requests(request):
    status = request.GET.get("status", "")
    requests = Project.objects.filter(requested_by_client=True).select_related(
        "client", "service", "assigned_staff"
    ).order_by("-created_at")
    if status:
        requests = requests.filter(status=status)
    return render(request, "admin_panel/requests.html", {"requests": paginate(request, requests), "status": status, "status_choices": Project.STATUS_CHOICES})


@admin_required
def admin_request_detail(request, id):
    project = get_object_or_404(Project.objects.select_related("client", "service", "assigned_staff"), id=id, requested_by_client=True)
    return render(request, "admin_panel/request_detail.html", {"project": project, "form": RequestApprovalForm(instance=project), "documents": project.documents.select_related("uploaded_by")})


@admin_required
def approve_request(request, id):
    project = get_object_or_404(Project, id=id, requested_by_client=True)
    form = RequestApprovalForm(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid():
        project = form.save(commit=False)
        project.approved_by = request.user
        project.approved_at = timezone.now()
        project.save()
        notify_user(project.client.user, "Request approved", f"Your request has been approved and assigned to {project.assigned_staff.full_name}.", "Request Approved", project)
        notify_user(project.assigned_staff.user, "New project assigned", f"You have been assigned to {project.title}.", "Project Assigned", project)
        send_request_approved_email(project)
        send_project_assigned_email(project)
        messages.success(request, "Request approved and assigned.")
        return redirect("management:admin_request_detail", id=project.id)
    return render(request, "admin_panel/request_detail.html", {"project": project, "form": form, "documents": project.documents.select_related("uploaded_by")})


@admin_required
def reject_request(request, id):
    project = get_object_or_404(Project, id=id, requested_by_client=True)
    project.status = "Cancelled"
    project.save(update_fields=["status", "updated_at"])
    notify_user(project.client.user, "Request rejected", f"Your request '{project.title}' was not accepted or has been cancelled.", "Request Rejected", project)
    send_request_rejected_email(project)
    messages.success(request, "Request rejected.")
    return redirect("management:admin_requests")


@admin_required
def admin_notifications(request):
    notifications = request.user.notifications.select_related("related_project")
    return render(request, "admin_panel/notifications.html", {"notifications": paginate(request, notifications)})


@admin_required
def admin_notification_read(request, id):
    notification = get_object_or_404(Notification, id=id, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    if notification.related_project and notification.related_project.requested_by_client:
        return redirect("management:admin_request_detail", id=notification.related_project_id)
    return redirect("management:admin_notifications")


from .decorators import client_required, staff_required


@client_required
def client_dashboard(request):
    client = request.user.client_profile
    projects = Project.objects.filter(client=client).select_related("service", "assigned_staff")
    payments = Payment.objects.filter(project__client=client).select_related("project").order_by("-created_at")
    documents = Document.objects.filter(project__client=client).select_related("project", "uploaded_by").order_by("-uploaded_at")
    today = timezone.localdate()
    context = {
        "client": client,
        "total_projects": projects.count(),
        "active_projects": projects.filter(status__in=ACTIVE_PROJECT_STATUSES).count(),
        "completed_projects": projects.filter(status="Completed").count(),
        "unpaid_projects": projects.filter(payment_status="Unpaid").count(),
        "deposit_projects": projects.filter(payment_status="Deposit Paid").count(),
        "fully_paid_projects": projects.filter(payment_status="Fully Paid").count(),
        "recent_documents": documents[:6],
        "recent_payments": payments[:6],
        "upcoming_deadlines": projects.filter(deadline__gte=today).exclude(status__in=["Completed", "Cancelled"]).order_by("deadline")[:6],
        "pending_requests": projects.filter(requested_by_client=True, status="Pending").count(),
    }
    return render(request, "client_panel/dashboard.html", context)


@client_required
def client_projects(request):
    client = request.user.client_profile
    projects = Project.objects.filter(client=client).select_related("service", "assigned_staff").order_by("-created_at")
    return render(request, "client_panel/projects.html", {"projects": paginate(request, projects)})


@client_required
def client_project_detail(request, id):
    client = request.user.client_profile
    project = get_object_or_404(Project.objects.select_related("service", "assigned_staff"), id=id, client=client)
    documents = project.documents.select_related("uploaded_by").order_by("-uploaded_at")
    payments = project.payments.order_by("-payment_date")
    progress_updates = project.progress_updates.select_related("updated_by")
    return render(
        request,
        "client_panel/project_detail.html",
        {
            "project": project,
            "documents": documents,
            "payments": payments,
            "progress_updates": progress_updates,
            "latest_progress": progress_updates.first(),
            "amount_paid": project_amount_paid(project),
            "balance_due": project_balance(project),
        },
    )


@client_required
def client_upload_document(request, id):
    client = request.user.client_profile
    project = get_object_or_404(Project, id=id, client=client)
    form = ClientDocumentUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        document = form.save(commit=False)
        document.project = project
        document.uploaded_by = request.user
        document.save()
        if project.assigned_staff:
            notify_user(project.assigned_staff.user, "New document uploaded", f"{client.full_name} uploaded a new document for {project.title}.", "Document Uploaded", project)
        else:
            notify_admins("New document uploaded", f"{client.full_name} uploaded a document for unassigned request {project.title}.", "Document Uploaded", project)
        messages.success(request, "Document uploaded.")
        return redirect("client:client_project_detail", id=project.id)
    return render(request, "client_panel/upload_document.html", {"form": form, "project": project})


@client_required
def client_documents(request):
    client = request.user.client_profile
    documents = Document.objects.filter(project__client=client).select_related("project", "uploaded_by").order_by("-uploaded_at")
    return render(request, "client_panel/documents.html", {"documents": paginate(request, documents)})


@client_required
def client_payments(request):
    client = request.user.client_profile
    payments = Payment.objects.filter(project__client=client).select_related("project", "project__service").order_by("-payment_date")
    return render(request, "client_panel/payments.html", {"payments": paginate(request, payments)})


@client_required
def client_payment_detail(request, id):
    client = request.user.client_profile
    payment = get_object_or_404(Payment.objects.select_related("project", "project__service", "project__client"), id=id, project__client=client)
    return render(request, "client_panel/payment_detail.html", {"payment": payment, "company_name": "TK Research"})


@client_required
def client_profile(request):
    client = request.user.client_profile
    form = ClientProfileForm(request.POST or None, instance=client)
    if request.method == "POST" and form.is_valid():
        client = form.save()
        client.user.email = client.email
        client.user.save(update_fields=["email"])
        messages.success(request, "Profile updated.")
        return redirect("client:client_profile")
    return render(request, "client_panel/profile.html", {"form": form, "client": client})


@client_required
def client_create_request(request):
    form = ClientRequestForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        project = form.save(commit=False)
        project.client = request.user.client_profile
        project.status = "Pending"
        project.payment_status = "Unpaid"
        project.assigned_staff = None
        project.requested_by_client = True
        project.save()
        upload = form.cleaned_data.get("supporting_file")
        if upload:
            Document.objects.create(project=project, uploaded_by=request.user, file=upload, document_type="Supporting File")
        notify_admins("New client request", f"{project.client.full_name} submitted a new request: {project.title}.", "New Request", project)
        messages.success(request, "Your request has been submitted successfully. Our team will review it and notify you once it is approved.")
        return redirect("client:client_request_detail", id=project.id)
    return render(request, "client_panel/request_form.html", {"form": form})


@client_required
def client_requests(request):
    projects = Project.objects.filter(client=request.user.client_profile, requested_by_client=True).select_related("service", "assigned_staff").order_by("-created_at")
    return render(request, "client_panel/requests.html", {"requests": paginate(request, projects)})


@client_required
def client_request_detail(request, id):
    project = get_object_or_404(Project.objects.select_related("service", "assigned_staff"), id=id, client=request.user.client_profile, requested_by_client=True)
    return render(request, "client_panel/request_detail.html", {"project": project, "documents": project.documents.select_related("uploaded_by"), "payments": project.payments.all(), "progress_updates": project.progress_updates.select_related("updated_by")})


@client_required
def client_notifications(request):
    notifications = request.user.notifications.select_related("related_project")
    return render(request, "client_panel/notifications.html", {"notifications": paginate(request, notifications)})


@client_required
def client_notification_read(request, id):
    notification = get_object_or_404(Notification, id=id, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    if notification.related_project:
        return redirect("client:client_project_detail", id=notification.related_project_id)
    return redirect("client:client_notifications")


@staff_required
def staff_portal_dashboard(request):
    staff = request.user.staff_profile
    projects = Project.objects.filter(assigned_staff=staff).select_related("client", "service")
    today = timezone.localdate()
    context = {
        "staff": staff,
        "total_projects": projects.count(),
        "active_projects": projects.filter(status__in=ACTIVE_PROJECT_STATUSES).count(),
        "completed_projects": projects.filter(status="Completed").count(),
        "under_review_projects": projects.filter(status="Under Review").count(),
        "recent_projects": projects.order_by("-created_at")[:6],
        "upcoming_deadlines": projects.filter(deadline__gte=today).exclude(status__in=["Completed", "Cancelled"]).order_by("deadline")[:6],
    }
    return render(request, "staff_panel/dashboard.html", context)


@staff_required
def staff_portal_projects(request):
    staff = request.user.staff_profile
    projects = Project.objects.filter(assigned_staff=staff).select_related("client", "service").order_by("deadline")
    return render(request, "staff_panel/projects.html", {"projects": paginate(request, projects)})


@staff_required
def staff_portal_project_detail(request, id):
    staff = request.user.staff_profile
    project = get_object_or_404(
        Project.objects.select_related("client", "service", "assigned_staff"),
        id=id,
        assigned_staff=staff,
    )
    documents = project.documents.select_related("uploaded_by").order_by("-uploaded_at")
    payments = project.payments.order_by("-payment_date")
    progress_updates = project.progress_updates.select_related("updated_by")
    return render(
        request,
        "staff_panel/project_detail.html",
        {
            "project": project,
            "documents": documents,
            "payments": payments,
            "progress_updates": progress_updates,
            "latest_progress": progress_updates.first(),
            "amount_paid": project_amount_paid(project),
            "balance_due": project_balance(project),
        },
    )


@staff_required
def staff_project_documents(request, id):
    staff = request.user.staff_profile
    project = get_object_or_404(Project, id=id, assigned_staff=staff)
    documents = project.documents.select_related("uploaded_by").order_by("-uploaded_at")
    return render(request, "staff_panel/documents.html", {"documents": paginate(request, documents), "project": project})


@staff_required
def staff_upload_document(request, id):
    staff = request.user.staff_profile
    project = get_object_or_404(Project, id=id, assigned_staff=staff)
    form = StaffDocumentUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        document = form.save(commit=False)
        document.project = project
        document.uploaded_by = request.user
        document.save()
        notify_user(project.client.user, "New document from your assigned staff", f"{staff.full_name} uploaded a document for {project.title}.", "Document Uploaded", project)
        notify_admins("Staff document uploaded", f"{staff.full_name} uploaded {document.document_type} for {project.title}.", "Document Uploaded", project)
        messages.success(request, "Document uploaded.")
        return redirect("staff:staff_project_detail", id=project.id)
    return render(request, "staff_panel/upload_document.html", {"project": project, "form": form})


@staff_required
def staff_progress_update(request, id):
    staff = request.user.staff_profile
    project = get_object_or_404(Project, id=id, assigned_staff=staff)
    form = ProgressUpdateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        update = form.save(commit=False)
        update.project = project
        update.updated_by = request.user
        update.save()
        if update.progress_percentage >= 1 and project.status in ["Pending", "Quoted"]:
            project.status = "In Progress"
            project.save(update_fields=["status", "updated_at"])
        elif update.progress_percentage == 100 and project.status != "Completed":
            project.status = "Under Review"
            project.save(update_fields=["status", "updated_at"])
        notify_user(project.client.user, "Project progress updated", f"{staff.full_name} posted a progress update for {project.title}: {update.progress_percentage}%.", "Project Updated", project)
        notify_admins("Project progress updated", f"{staff.full_name} updated {project.title} to {update.progress_percentage}%.", "Project Updated", project)
        messages.success(request, "Progress update posted.")
        return redirect("staff:staff_project_detail", id=project.id)
    return render(request, "staff_panel/progress_update.html", {"project": project, "form": form})


@staff_required
def staff_portal_documents(request):
    staff = request.user.staff_profile
    documents = Document.objects.filter(project__assigned_staff=staff).select_related("project", "uploaded_by").order_by("-uploaded_at")
    return render(request, "staff_panel/documents.html", {"documents": paginate(request, documents)})


@staff_required
def staff_notifications(request):
    notifications = request.user.notifications.select_related("related_project")
    return render(request, "staff_panel/notifications.html", {"notifications": paginate(request, notifications)})


@staff_required
def staff_notification_read(request, id):
    notification = get_object_or_404(Notification, id=id, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    if notification.related_project:
        return redirect("staff:staff_project_detail", id=notification.related_project_id)
    return redirect("staff:staff_notifications")


@staff_required
def staff_portal_profile(request):
    staff = request.user.staff_profile
    return render(request, "staff_panel/profile.html", {"staff": staff})
