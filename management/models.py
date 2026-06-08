from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator


class Client(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="client_profile"
    )
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField()
    institution = models.CharField(max_length=200, blank=True, null=True)
    must_change_password = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


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
    )

    PAYMENT_STATUS_CHOICES = (
        ("Unpaid", "Unpaid"),
        ("Deposit Paid", "Deposit Paid"),
        ("Fully Paid", "Fully Paid"),
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
    approved_at = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="approved_projects"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    uploaded_at = models.DateTimeField(auto_now_add=True)

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

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.project.title} - {self.amount}"


class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = (
        ("New Request", "New Request"),
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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.project.title} - {self.progress_percentage}%"
