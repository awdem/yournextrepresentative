import elections.api.next.api_views
import parties.api.next.api_views
import people.api.next.api_views
from api import slack_hooks
from api.next import views as next_views
from api.v09 import views as v09views
from api.views import (
    APIDocsDefinitionsView,
    APIDocsEndpointsView,
    NextAPIDocsView,
    ResultsDocs,
)
from django.urls import include, re_path
from django.views.decorators.cache import cache_page
from django.views.generic import RedirectView, TemplateView
from facebook_data.api.next.views import FacebookAdvertViewSet
from parties.api.next.api_views import (
    CurrentPartyNamesCSVView,
    PartyRegisterList,
    PartyViewSet,
)
from rest_framework import routers
from uk_results.api.next.api_views import ElectedViewSet, ResultViewSet
from uk_results.api.v09.api_views import (
    CandidateResultViewSet,
    ResultSetViewSet,
)

v09_api_router = routers.DefaultRouter()

v09_api_router.register(r"persons", v09views.PersonViewSet, basename="person")
v09_api_router.register(r"organizations", v09views.OrganizationViewSet)
v09_api_router.register(r"posts", v09views.PostViewSet)
v09_api_router.register(r"elections", v09views.ElectionViewSet)
v09_api_router.register(r"party_sets", v09views.PartySetViewSet)
v09_api_router.register(r"post_elections", v09views.PostExtraElectionViewSet)
v09_api_router.register(r"memberships", v09views.MembershipViewSet)
v09_api_router.register(r"logged_actions", v09views.LoggedActionViewSet)
v09_api_router.register(
    r"extra_fields", v09views.ExtraFieldViewSet, basename="extra_fields"
)
v09_api_router.register(r"person_redirects", v09views.PersonRedirectViewSet)

v09_api_router.register(r"candidate_results", CandidateResultViewSet)
v09_api_router.register(r"result_sets", ResultSetViewSet)

v09_api_router.register(
    r"candidates_for_postcode",
    v09views.CandidatesAndElectionsForPostcodeViewSet,
    basename="candidates-for-postcode",
)

# "Next" is the label we give to the "bleeding edge" or unstable API
next_api_router = routers.DefaultRouter()
next_api_router.register(
    r"people", people.api.next.api_views.PersonViewSet, basename="person"
)
next_api_router.register(r"organizations", next_views.OrganizationViewSet)
next_api_router.register(
    r"elections", elections.api.next.api_views.ElectionViewSet
)
next_api_router.register(
    r"election_types",
    elections.api.next.api_views.ElectionTypesList,
    basename="election_types",
)
next_api_router.register(r"ballots", elections.api.next.api_views.BallotViewSet)
next_api_router.register(r"logged_actions", next_views.LoggedActionViewSet)
next_api_router.register(
    r"person_redirects", people.api.next.api_views.PersonRedirectViewSet
)

next_api_router.register(r"parties", PartyViewSet)
next_api_router.register(
    r"current_parties_csv",
    CurrentPartyNamesCSVView,
    basename="current_parties_csv",
)
next_api_router.register(
    r"party_registers", PartyRegisterList, basename="party_register"
)
next_api_router.register(r"results", ResultViewSet)
next_api_router.register(r"candidates_elected", ElectedViewSet)
next_api_router.register(r"facebook_adverts", FacebookAdvertViewSet)

urlpatterns = [
    # Router views
    re_path(r"^api/(?P<version>v0.9)/", include(v09_api_router.urls)),
    re_path(r"^api/(?P<version>next)/", include(next_api_router.urls)),
    re_path(
        r"^api/docs/$",
        TemplateView.as_view(template_name="api/api-home.html"),
        name="api-home",
    ),
    re_path(
        r"^api/$",
        RedirectView.as_view(url="/api/docs/"),
        name="api-docs-redirect",
    ),
    re_path(
        r"^api/docs/terms/$",
        TemplateView.as_view(template_name="api/terms.html"),
        name="api-terms",
    ),
    re_path(r"^api/docs/atom/$", ResultsDocs.as_view(), name="api_docs_atom"),
    re_path(
        r"^api/docs/next/$",
        NextAPIDocsView.as_view(patterns=next_api_router.urls, version="next"),
        name="api_docs_next_home",
    ),
    re_path(
        r"^api/docs/next/endpoints/$",
        APIDocsEndpointsView.as_view(
            patterns=next_api_router.urls, version="next"
        ),
        name="api_docs_next_endpoints",
    ),
    re_path(
        r"^api/docs/next/definitions/$",
        APIDocsDefinitionsView.as_view(
            patterns=next_api_router.urls, version="next"
        ),
        name="api_docs_next_definitions",
    ),
    # Standard Django views
    re_path(
        r"^api/current-elections",
        v09views.CurrentElectionsView.as_view(),
        name="current-elections",
    ),
    re_path(
        r"^all-parties.json$",
        cache_page(60 * 60)(
            parties.api.next.api_views.AllPartiesJSONView.as_view()
        ),
        name="all-parties-json-view",
    ),
    re_path(r"^version.json", v09views.VersionView.as_view(), name="version"),
    re_path(
        r"^upcoming-elections",
        v09views.UpcomingElectionsView.as_view(),
        name="upcoming-elections",
    ),
    re_path("api/slack-hooks", slack_hooks.SlackHookRouter.as_view()),
]
