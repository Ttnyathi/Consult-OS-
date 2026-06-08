from django.contrib import admin

from .models import Client, Document, Payment, Project, Service, StaffProfile


admin.site.site_header = "TK Research Management"
admin.site.site_title = "TK Research Admin"
admin.site.index_title = "Management records"


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "phone", "institution", "created_at")
    search_fields = ("full_name", "email", "institution")
    list_filter = ("created_at",)


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "role", "phone", "is_active", "created_at")
    search_fields = ("full_name", "user__username", "phone")
    list_filter = ("role", "is_active", "created_at")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "base_price", "estimated_days", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "client",
        "service",
        "assigned_staff",
        "status",
        "payment_status",
        "deadline",
        "quoted_price",
    )
    search_fields = ("title", "client__full_name", "client__email")
    list_filter = ("status", "payment_status", "service", "deadline")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("project", "document_type", "uploaded_by", "uploaded_at")
    search_fields = ("project__title", "uploaded_by__username")
    list_filter = ("document_type", "uploaded_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("project", "amount", "payment_method", "status", "payment_date")
    search_fields = ("project__title", "reference")
    list_filter = ("payment_method", "status", "payment_date")
