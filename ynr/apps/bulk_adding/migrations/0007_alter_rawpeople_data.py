# Generated by Django 3.2.4 on 2021-09-28 09:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("bulk_adding", "0006_auto_20210401_0811")]

    operations = [
        migrations.AlterField(
            model_name="rawpeople", name="data", field=models.JSONField()
        )
    ]
