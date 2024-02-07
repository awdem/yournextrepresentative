# Generated by Django 4.2.6 on 2023-11-06 13:37

import django.db.models.deletion
import django_extensions.db.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("official_documents", "0028_alter_officialdocument_uploaded_file"),
    ]

    operations = [
        migrations.CreateModel(
            name="TextractResult",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created",
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name="modified"
                    ),
                ),
                ("job_id", models.CharField(max_length=100)),
                ("json_response", models.JSONField()),
                (
                    "official_document",
                    models.OneToOneField(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="textract_result",
                        to="official_documents.officialdocument",
                    ),
                ),
            ],
            options={
                "get_latest_by": "modified",
                "abstract": False,
            },
        ),
    ]