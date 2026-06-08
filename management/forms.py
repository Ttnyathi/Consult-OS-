from django import forms
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string

from .models import Client, Document, Payment, ProgressUpdate, Project, Service, StaffProfile


TEMP_PASSWORD_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$"


def generate_temporary_password():
    return get_random_string(length=10, allowed_chars=TEMP_PASSWORD_CHARS)


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["full_name", "phone", "email", "institution"]


class ClientCreateForm(ClientForm):
    username = forms.CharField(max_length=150)

    class Meta(ClientForm.Meta):
        fields = ["username", "full_name", "phone", "email", "institution"]

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        self.temporary_password = generate_temporary_password()
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password=self.temporary_password,
        )
        client = Client(
            user=user,
            full_name=self.cleaned_data["full_name"],
            phone=self.cleaned_data["phone"],
            email=self.cleaned_data["email"],
            institution=self.cleaned_data["institution"],
            must_change_password=True,
        )
        if commit:
            client.save()
        return client


class StaffProfileForm(forms.ModelForm):
    class Meta:
        model = StaffProfile
        fields = ["full_name", "phone", "role", "is_active"]


class StaffCreateForm(StaffProfileForm):
    username = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)

    class Meta(StaffProfileForm.Meta):
        fields = ["username", "email", "full_name", "phone", "role", "is_active"]

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        role = self.cleaned_data["role"]
        self.temporary_password = generate_temporary_password()
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data.get("email") or "",
            password=self.temporary_password,
        )
        user.is_staff = role == "Admin"
        user.save()
        staff = StaffProfile(
            user=user,
            full_name=self.cleaned_data["full_name"],
            phone=self.cleaned_data["phone"],
            role=role,
            is_active=self.cleaned_data["is_active"],
            must_change_password=True,
        )
        if commit:
            staff.save()
        return staff


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "description", "base_price", "estimated_days", "is_active"]


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "client",
            "service",
            "assigned_staff",
            "title",
            "description",
            "deadline",
            "status",
            "quoted_price",
            "payment_status",
        ]
        widgets = {
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_staff"].queryset = StaffProfile.objects.filter(
            is_active=True
        )
        self.fields["assigned_staff"].required = False
        self.fields["service"].required = False
        self.fields["quoted_price"].required = False


class AssignProjectForm(forms.ModelForm):
    move_to_in_progress = forms.BooleanField(
        required=False,
        initial=True,
        label="Move pending or quoted project to In Progress",
    )

    class Meta:
        model = Project
        fields = ["assigned_staff"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_staff"].queryset = StaffProfile.objects.filter(
            is_active=True
        )
        self.fields["assigned_staff"].required = False


class ProjectStatusForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["status", "payment_status"]


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["project", "file", "document_type"]


class ClientDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["file", "document_type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = ["Client Upload", "Supporting File"]
        self.fields["document_type"].choices = [
            choice for choice in Document.DOCUMENT_TYPE_CHOICES if choice[0] in allowed
        ]


class StaffDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["file", "document_type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = ["Draft", "Final Work", "Plagiarism Report", "Supporting File"]
        self.fields["document_type"].choices = [
            choice for choice in Document.DOCUMENT_TYPE_CHOICES if choice[0] in allowed
        ]


class ClientRequestForm(forms.ModelForm):
    supporting_file = forms.FileField(required=False)

    class Meta:
        model = Project
        fields = ["service", "title", "description", "deadline", "supporting_file"]
        widgets = {
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.filter(is_active=True)


class RequestApprovalForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["quoted_price", "assigned_staff", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_staff"].queryset = StaffProfile.objects.filter(is_active=True)
        self.fields["status"].choices = [
            ("Quoted", "Quoted"),
            ("In Progress", "In Progress"),
        ]
        self.fields["quoted_price"].required = True
        self.fields["assigned_staff"].required = True


class ProgressUpdateForm(forms.ModelForm):
    class Meta:
        model = ProgressUpdate
        fields = ["title", "message", "progress_percentage"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4}),
        }


class ClientProfileForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["full_name", "phone", "email", "institution"]


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            "project",
            "amount",
            "payment_method",
            "reference",
            "payment_date",
            "status",
        ]
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}),
        }
