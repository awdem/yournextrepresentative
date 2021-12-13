# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-09-03 13:55
from __future__ import unicode_literals

from django.db import migrations


def copy_org_to_party(apps, schema_editor):
    """
    This one is a little fiddly because:

    1. We want to assign a Party object to each Membership. At the time this
       migration runs, we might not have anything in the `Party` table.

    2. Currently the "party" is an Organization object with a classification of
       `Party`. The identifier for the party is a generic relation to
       Identifier.

    3. Because of the way that Django's `apps.get_model` works, it prevents
       GenericRelations from working in migrations. This means we need to
       construct some of the relation ourselves.

    To get around all of these, we need to:

    1. Get the content type ID for Organization
    2. Get all Identifier objects with that content type
    3. Store all the Identifiers with the scheme "electoral-commission" in a
       dict (ORG_PK_TO_EC_IDS) with the org PK as the key.
    4. Store all the Identifiers with a different scheme in a dict
       (ORG_PK_TO_OTHER_IDS) with the org PK as the key.
    5. Iterate over all Organisations with the classification of "Party" and:
        1. Get the best ID for this party (prefer the EC ID, fall back to the
           OTHER ID or slug)
        2. update_or_create a Party object
        3. Store all the parties and orgs in a dict with org as the key
    6. Iterate over the map between object types
    7. Filter Membership objects by the organisation object ID and update it
       with the party object.

    Note that this migration doesn't remove any data, just copies it in to a
    different format / model / field.
    """

    Membership = apps.get_model("popolo", "Membership")
    Party = apps.get_model("parties", "Party")
    Organization = apps.get_model("popolo", "Organization")
    Identifier = apps.get_model("popolo", "Identifier")
    ContentType = apps.get_model("contenttypes", "ContentType")

    organization_content_type_id = ContentType.objects.get_for_model(
        Organization
    ).pk

    #  Set up the maps we'll need
    ORG_PK_TO_EC_IDS = {}
    ORG_OBJ_TO_PARTY_OBJ = {}

    # Get all the IDs used for Organizations
    ids_qs = Identifier.objects.filter(
        content_type_id=organization_content_type_id,
        scheme="electoral-commission",
    )

    # Populate the maps with the IDs for each organisation
    for identifier in ids_qs:
        ORG_PK_TO_EC_IDS[identifier.object_id] = identifier.identifier

    # Get all Organisations that are parties
    all_org_parties = Organization.objects.filter(classification="Party")

    for org_party in all_org_parties:
        # First we need an ID for this party.
        # This could take the form of an EC ID (PP01) or a psudo-party ID we've
        # assigned in the past (ynmp-party:2), or a slug (joint-party:1-2)
        # preferred in that order.

        if org_party.pk in ORG_PK_TO_EC_IDS:
            party_id = ORG_PK_TO_EC_IDS[org_party.pk]
        else:
            party_id = org_party.extra.slug

        start_date = org_party.start_date
        if not start_date:
            # This is a hack around some parties in the live DB not having a
            # start date. As we have no way of knowing in this migration what
            # the correct value is, but the new Party model requires a
            # `date_registered`, we have to use something. Let's just use
            # the date the object was created. This has the benefit of not
            # causing an internal integrity error as no memberships will exist
            # for this party before it existed in our DB and should fix itself
            # when the parties importer is run first / next
            start_date = org_party.created_at

        # Update or create the party, using the "EC ID" that will be used by the
        # party importer
        party_obj, _ = Party.objects.update_or_create(
            ec_id=party_id,
            defaults={"name": org_party.name, "date_registered": start_date},
        )

        # Populate the map from the org object to the party object
        ORG_OBJ_TO_PARTY_OBJ[org_party] = party_obj

    for org_party, party_obj in ORG_OBJ_TO_PARTY_OBJ.items():
        # Update the memberships for this org
        Membership.objects.filter(on_behalf_of_id=org_party).update(
            party=party_obj
        )

    # Just make sure no memberships are left without a Party
    assert Membership.objects.filter(party=None).count() == 0

    # These numbers should be identical
    if Party.objects.count() < all_org_parties.count():
        raise ValueError("More Organzation parties than Parties")


class Migration(migrations.Migration):

    dependencies = [("popolo", "0014_membership_party")]

    operations = [
        migrations.RunPython(copy_org_to_party, migrations.RunPython.noop)
    ]
