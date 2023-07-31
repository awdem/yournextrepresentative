from unittest.mock import patch

from candidates.models import LoggedAction
from candidates.models.db import ActionType
from candidates.tests.auth import TestUserMixin
from candidates.tests.factories import faker_factory
from candidates.tests.helpers import TmpMediaRootMixin
from candidates.tests.uk_examples import UK2015ExamplesMixin
from django.contrib.auth import get_user_model
from django_webtest import WebTest
from moderation_queue.models import QueuedImage
from moderation_queue.tests.paths import EXAMPLE_IMAGE_FILENAME
from people.models import Person, PersonImage
from people.tests.factories import PersonFactory
from popolo.models import Membership
from sorl.thumbnail import get_thumbnail


class TestPersonModels(
    TestUserMixin, UK2015ExamplesMixin, TmpMediaRootMixin, WebTest
):
    def setUp(self):
        super().setUp()

    def test_get_display_image_url(self):
        person = PersonFactory(name=faker_factory.name())

        self.assertEqual(
            person.get_display_image_url(),
            "/static/candidates/img/blank-person.png",
        )

        pi = PersonImage.objects.create_from_file(
            filename=EXAMPLE_IMAGE_FILENAME,
            new_filename="images/jowell-pilot.jpg",
            defaults={
                "person": person,
                "source": "Taken from Wikipedia",
                "copyright": "example-license",
                "user_notes": "A photo of Tessa Jowell",
            },
        )

        url = get_thumbnail(pi.image, "x64").url
        # fresh lookup of the instance is required in order to invalidate the
        # cached value of person_image
        person = Person.objects.get()
        self.assertEqual(person.get_display_image_url(), url)

    def test_get_alive_now(self):
        alive_person = PersonFactory(name=faker_factory.name())
        PersonFactory(name=faker_factory.name(), death_date="2016-01-01")
        qs = Person.objects.alive_now()
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.get(), alive_person)

    def test_current_elections_standing_down(self):
        person = PersonFactory(name=faker_factory.name())
        self.assertEqual(person.current_elections_standing_down(), [])
        Membership.objects.create(
            ballot=self.dulwich_post_ballot_earlier,
            party=self.ld_party,
            person=person,
            elected=True,
        )

        person.not_standing.add(self.election)
        self.assertEqual(
            person.current_elections_standing_down(), [self.election]
        )

    def test_current_elections_not_standing_then_standing_again(self):
        # This is a test for when a person is marked as not standing in an
        # election, but then later is marked as standing in that same election.
        # This can happen if a person is marked as not standing in an election
        # and then later is added to the ballot paper.
        ballot = self.election.ballot_set.first()
        self.person = PersonFactory()
        self.assertEqual(self.person.not_standing.all().count(), 0)
        self.person.not_standing.add(ballot.election)

        # adding a person to a ballot removes the ballot from that person's not standing list
        response = self.app.get(
            f"/person/{self.person.id}/update", user=self.user, auto_follow=True
        )
        form = response.forms["person-details"]
        form["memberships-0-ballot_paper_id"].value = ballot.ballot_paper_id
        form["memberships-0-party_identifier_0"].value = self.labour_party.ec_id
        form[
            "source"
        ] = "Test adding a person to a ballot removes them from the not standing list"
        form.submit()

        # check that the person is no longer marked as not standing in the election
        self.assertEqual(self.person.not_standing.all().count(), 0)

    def test_delete_with_logged_action(self):
        """
        Test that the Person.delete_with_logged_action deletes the objects and
        creates a single logged action with the user assigned
        """
        person = PersonFactory()
        person_pk = person.pk
        user = get_user_model().objects.create()

        person.delete_with_logged_action(
            user=user, source="Test a single logged action is created"
        )
        logged_actions = LoggedAction.objects.filter(
            person_pk=person_pk, action_type=ActionType.PERSON_DELETE
        )

        self.assertEqual(logged_actions.count(), 1)
        self.assertEqual(logged_actions.first().user, user)
        self.assertFalse(Person.objects.filter(pk=person_pk).exists())

    def test_delete_signal(self):
        """
        Test that the standard delete will still create a logged action, but
        without a user
        """
        person = PersonFactory()
        person_pk = person.pk

        person.delete()
        logged_actions = LoggedAction.objects.filter(
            person_pk=person_pk, action_type=ActionType.PERSON_DELETE
        )

        self.assertEqual(logged_actions.count(), 1)
        self.assertIsNone(logged_actions.first().user)
        self.assertFalse(Person.objects.filter(pk=person_pk).exists())

    def test_something_goes_wrong_with_delete(self):
        """
        If the person delete fails for some reason check the logged action was
        not created becasue we are using transaction.atomic
        """
        person = PersonFactory()
        person_pk = person.pk
        user = get_user_model().objects.create()

        with patch.object(person, "delete", side_effect=Exception):
            # catch the exception so we can do
            try:
                person.delete_with_logged_action(
                    user=user, source="Test a logged action isnt created"
                )
            except Exception:
                self.assertFalse(
                    LoggedAction.objects.filter(
                        person_pk=person_pk,
                        action_type=ActionType.PERSON_DELETE,
                    ).exists()
                )

    def test_queued_image(self):
        user = get_user_model().objects.create()
        person = PersonFactory()
        expected = QueuedImage.objects.create(
            user=user, person=person, image=EXAMPLE_IMAGE_FILENAME
        )
        self.assertEqual(person.queued_image, expected)

    def test_get_absolute_queued_image_url(self):
        user = get_user_model().objects.create()
        person = PersonFactory()
        queued_image = QueuedImage.objects.create(
            user=user, person=person, image=EXAMPLE_IMAGE_FILENAME
        )
        self.assertEqual(
            person.get_absolute_queued_image_url(),
            "/moderation/photo/review/{}".format(queued_image.id),
        )
