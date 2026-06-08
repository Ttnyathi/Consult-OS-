# Generated manually for first-login password change flow.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("management", "0002_payment_created_at_alter_document_uploaded_by_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="must_change_password",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="staffprofile",
            name="must_change_password",
            field=models.BooleanField(default=True),
        ),
    ]
