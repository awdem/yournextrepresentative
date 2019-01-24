# -*- coding: utf-8 -*-
# Generated by Django 1.11.18 on 2019-01-19 18:25
from __future__ import unicode_literals

from django.db import migrations


def move_person_identifiers(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    PersonIdentifier = apps.get_model("people", "PersonIdentifier")
    Person = apps.get_model("people", "Person")
    Identifier = apps.get_model("popolo", "Identifier")

    person_content_type_id = ContentType.objects.get_for_model(Person).pk
    qs = Identifier.objects.filter(
        content_type_id=person_content_type_id, scheme="uk.org.publicwhip"
    )
    for identifier in qs:
        public_whip_id = identifier.identifier.split("/")[-1]
        PersonIdentifier.objects.update_or_create(
            person_id=identifier.object_id,
            value="https://www.theyworkforyou.com/mp/{}/".format(
                public_whip_id
            ),
            value_type="theyworkforyou",
            internal_identifier=identifier.identifier,
        )


class Migration(migrations.Migration):

    dependencies = [("ynr_refactoring", "0002_move_old_election_slugs")]

    operations = [
        migrations.RunPython(move_person_identifiers, migrations.RunPython.noop)
    ]
