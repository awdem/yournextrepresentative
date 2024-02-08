# Generated by Django 4.2.8 on 2024-02-08 15:03

import parties.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("parties", "0022_party_nations"),
    ]

    operations = [
        migrations.AlterField(
            model_name="partyemblem",
            name="image",
            field=models.ImageField(
                max_length=255, upload_to=parties.models.emblem_upload_path
            ),
        ),
    ]