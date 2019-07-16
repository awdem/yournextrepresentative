from django.views.generic import CreateView, DetailView, TemplateView
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404

from auth_helpers.views import GroupRequiredMixin
from elections.mixins import ElectionMixin
from moderation_queue.models import SuggestedPostLock

from .forms import UploadDocumentForm
from .models import DOCUMENT_UPLOADERS_GROUP_NAME, OfficialDocument

from popolo.models import Post
from candidates.models import is_post_locked, Ballot, LoggedAction
from candidates.views import get_client_ip


class CreateDocumentView(ElectionMixin, GroupRequiredMixin, CreateView):
    required_group_name = DOCUMENT_UPLOADERS_GROUP_NAME

    form_class = UploadDocumentForm
    template_name = "official_documents/upload_document_form.html"

    def get_initial(self):
        post = get_object_or_404(Post, slug=self.kwargs["post_id"])
        ballot = Ballot.objects.get(post=post, election=self.election_data)
        return {
            "election": self.election_data,
            "document_type": OfficialDocument.NOMINATION_PAPER,
            "post": post,
            "ballot": ballot,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = get_object_or_404(Post, slug=self.kwargs["post_id"])
        context["post_label"] = post.label
        return context

    def form_valid(self, form):
        LoggedAction.objects.create(
            user=self.request.user,
            post_election=form.instance.ballot,
            action_type="sopn-upload",
            ip_address=get_client_ip(self.request),
            source=form.cleaned_data["source_url"],
        )
        return super().form_valid(form)


class PostsForDocumentView(DetailView):
    model = OfficialDocument
    template_name = "official_documents/posts_for_document.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        documents = (
            OfficialDocument.objects.filter(source_url=self.object.source_url)
            .filter(ballot__election=self.object.ballot.election)
            .select_related("ballot__post", "ballot__election")
            .order_by("ballot__ballot_paper_id")
            .prefetch_related("ballot__suggestedpostlock_set")
        )

        context["document_posts"] = documents

        return context


def get_add_from_document_cta_flash_message(document, remaining_posts):
    return render_to_string(
        "official_documents/_add_from_document_cta_flash_message.html",
        {"document": document, "remaining_posts": remaining_posts},
    )


class UnlockedWithDocumentsView(TemplateView):
    template_name = "official_documents/unlocked_with_documents.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        SOPNs_qs = OfficialDocument.objects.filter(
            ballot__election__current=True
        ).select_related("ballot__election", "ballot__post")

        SOPNs_qs = SOPNs_qs.exclude(
            ballot__post__in=SuggestedPostLock.objects.all().values(
                "ballot__post"
            )
        )

        context["unlocked_sopns"] = SOPNs_qs.filter(
            ballot__candidates_locked=False
        )

        return context
