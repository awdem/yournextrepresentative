# Generated by Django 3.2.4 on 2021-09-28 09:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("candidates", "0071_add_created_data")]

    operations = [
        migrations.AlterModelOptions(
            name="ballot", options={"get_latest_by": "modified"}
        )
    ]