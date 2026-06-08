from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone


class Client(models.Model):
    STATUS_CHOICES = (
        ("Limited", "Limited Access"),
        ("Pending Review", "Pending Review"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
        ("Suspended", "Suspended"),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="client_profile"
    )
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField()
    institution = models.CharField(max_length=200, blank=True, null=True)

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default="Limited"
    )

    must_change_password = models.BooleanField(default=False)

    max_open_requests = models.PositiveIntegerField(default=3)

    approved_at = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="approved_clients"
    )

    rejected_at = models.DateTimeField(blank=True, null=True)
    rejected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="rejected_clients"
    )
    rejection_reason = models.TextField(blank=True, null=True)

    suspended_at = models.DateTimeField(blank=True, null=True)
    suspended_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="suspended_clients"
    )
    suspension_reason = models.TextField(blank=True, null=True)

    admin_notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_limited(self):
        return self.status == "Limited"

    @property
    def is_pending_review(self):
        return self.status == "Pending Review"

    @property
    def is_approved(self):
        return self.status == "Approved"

    @property
    def is_rejected(self):
        return self.status == "Rejected"

    @property
    def is_suspended(self):
        return self.status == "Suspended"

    @property
    def can_create_request(self):
        return self.status in ["Limited", "Pending Review", "Approved"]

    @property
    def has_full_access(self):
        return self.status == "Approved"

    def open_request_count(self):
        return self.projects.exclude(
            status__in=["Completed", "Cancelled", "Rejected"]
        ).count()

    def has_reached_request_limit(self):
        if self.is_approved:
            return False

        return self.open_request_count() >= self.max_open_requests

    def approve(self, admin_user):
        self.status = "Approved"
        self.approved_by = admin_user
        self.approved_at = timezone.now()
        self.rejected_at = None
        self.rejected_by = None
        self.rejection_reason = None
        self.suspended_at = None
        self.suspended_by = None
        self.suspension_reason = None
        self.save()

    def reject(self, admin_user, reason=""):
        self.status = "Rejected"
        self.rejected_by = admin_user
        self.rejected_at = timezone.now()
        self.rejection_reason = reason
        self.save()

    def suspend(self, admin_user=None, reason=""):
        self.status = "Suspended"
        self.suspended_by = admin_user
        self.suspended_at = timezone.now()
        self.suspension_reason = reason
        self.save()

    def move_to_pending_review(self):
        if self.status == "Limited":
            self.status = "Pending Review"
            self.save()

    def __str__(self):
        return f"{self.full_name} - {self.status}"


class StaffProfile(models.Model):
    ROLE_CHOICES = (
        ("Admin", "Admin"),
        ("Consultant", "Consultant"),
        ("Writer", "Writer"),
        ("Analyst", "Analyst"),
        ("Editor", "Editor"),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="staff_profile"
    )
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30, blank=True, null=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    must_change_password = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_admin(self):
        return self.role == "Admin"

    def __str__(self):
        return f"{self.full_name} - {self.role}"


class Service(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_days = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Quoted", "Quoted"),
        ("In Progress", "In Progress"),
        ("Under Review", "Under Review"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
        ("Rejected", "Rejected"),
    )

    PAYMENT_STATUS_CHOICES = (
        ("Unpaid", "Unpaid"),
        ("Deposit Paid", "Deposit Paid"),
        ("Fully Paid", "Fully Paid"),
    )

    REQUEST_ACCESS_CHOICES = (
        ("Limited Client", "Limited Client"),
        ("Approved Client", "Approved Client"),
        ("Staff Created", "Staff Created"),
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="projects"
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects"
    )

    assigned_staff = models.ForeignKey(
        StaffProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_projects"
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    deadline = models.DateField()

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    quoted_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    payment_status = models.CharField(
        max_length=50,
        choices=PAYMENT_STATUS_CHOICES,
        default="Unpaid"
    )

    requested_by_client = models.BooleanField(default=False)

    request_access_type = models.CharField(
        max_length=50,
        choices=REQUEST_ACCESS_CHOICES,
        default="Staff Created"
    )

    approved_at = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="approved_projects"
    )

    rejected_at = models.DateTimeField(blank=True, null=True)
    rejected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="rejected_projects"
    )
    rejection_reason = models.TextField(blank=True, null=True)

    admin_notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_active_project(self):
        return self.status not in ["Completed", "Cancelled", "Rejected"]

    def approve_project(self, admin_user):
        self.approved_by = admin_user
        self.approved_at = timezone.now()
        self.status = "Quoted"
        self.save()

    def reject_project(self, admin_user, reason=""):
        self.rejected_by = admin_user
        self.rejected_at = timezone.now()
        self.rejection_reason = reason
        self.status = "Rejected"
        self.save()

    def __str__(self):
        return self.title


class Document(models.Model):
    DOCUMENT_TYPE_CHOICES = (
        ("Client Upload", "Client Upload"),
        ("Draft", "Draft"),
        ("Final Work", "Final Work"),
        ("Plagiarism Report", "Plagiarism Report"),
        ("Supporting File", "Supporting File"),
    )

    ACCESS_LEVEL_CHOICES = (
        ("Client Visible", "Client Visible"),
        ("Staff Only", "Staff Only"),
        ("Admin Only", "Admin Only"),
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents"
    )

    file = models.FileField(upload_to="project_documents/")
    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPE_CHOICES
    )

    access_level = models.CharField(
        max_length=50,
        choices=ACCESS_LEVEL_CHOICES,
        default="Client Visible"
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_client_visible(self):
        return self.access_level == "Client Visible"

    def __str__(self):
        return f"{self.project.title} - {self.document_type}"


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ("Cash", "Cash"),
        ("Bank Transfer", "Bank Transfer"),
        ("EcoCash", "EcoCash"),
        ("PayPal", "PayPal"),
        ("Other", "Other"),
    )

    PAYMENT_STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Confirmed", "Confirmed"),
        ("Failed", "Failed"),
        ("Refunded", "Refunded"),
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHOD_CHOICES
    )

    reference = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    payment_date = models.DateField()

    status = models.CharField(
        max_length=50,
        choices=PAYMENT_STATUS_CHOICES,
        default="Pending"
    )

    confirmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="confirmed_payments"
    )

    confirmed_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def confirm_payment(self, admin_user):
        self.status = "Confirmed"
        self.confirmed_by = admin_user
        self.confirmed_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.project.title} - {self.amount}"


class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = (
        ("New Request", "New Request"),
        ("Account Created", "Account Created"),
        ("Account Approved", "Account Approved"),
        ("Account Rejected", "Account Rejected"),
        ("Account Suspended", "Account Suspended"),
        ("Request Approved", "Request Approved"),
        ("Request Rejected", "Request Rejected"),
        ("Project Assigned", "Project Assigned"),
        ("Project Updated", "Project Updated"),
        ("Payment Updated", "Payment Updated"),
        ("Document Uploaded", "Document Uploaded"),
    )

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPE_CHOICES
    )
    related_project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )
    related_client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient.username} - {self.title}"


class ProgressUpdate(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="progress_updates"
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="progress_updates"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    progress_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    client_visible = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.project.title} - {self.progress_percentage}%"