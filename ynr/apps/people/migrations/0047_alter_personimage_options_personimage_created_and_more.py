# Generated by Django 4.2.11 on 2024-07-02 13:44

import django.utils.timezone
import django_extensions.db.fields
from django.db import migrations


def get_timestamp_from_queued_image(apps, schema_editor):
    """Set the created and modified timestamps on the image
    to the timestamp of the first and last approved queued image"""

    PersonImage = apps.get_model("people", "PersonImage")
    for personimage in PersonImage.objects.all():
        person = personimage.person
        queued_images = person.queuedimage_set.filter(decision="approved")
        if not queued_images:
            continue
        modified = queued_images.last().updated
        created = queued_images.last().created
        if modified:
            personimage.modified = modified
            personimage.created = created
            personimage.save()


class Migration(migrations.Migration):
    dependencies = [
        ("people", "0046_alter_personidentifier_unique_together"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="personimage",
            options={"get_latest_by": "modified"},
        ),
        migrations.AddField(
            model_name="personimage",
            name="created",
            field=django_extensions.db.fields.CreationDateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                verbose_name="created",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="personimage",
            name="modified",
            field=django_extensions.db.fields.ModificationDateTimeField(
                auto_now=True, verbose_name="modified"
            ),
        ),
        (
            migrations.RunPython(
                get_timestamp_from_queued_image, migrations.RunPython.noop
            )
        ),
    ]
