# Generated by Django 2.2.19 on 2021-03-28 11:55

from django.db import migrations

from people.managers import NAME_SEARCH_TRIGGER_SQL


class Migration(migrations.Migration):

    dependencies = [("people", "0024_add_gist_index_for_search")]

    operations = [migrations.RunSQL(NAME_SEARCH_TRIGGER_SQL)]
