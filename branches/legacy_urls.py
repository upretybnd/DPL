"""Old /branch/... addresses, kept as permanent redirects so existing links and search results keep working."""
from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path('branches/', RedirectView.as_view(pattern_name='branch_details', permanent=True, query_string=True)),
    path('branch/<int:branch_id>/', views.legacy_branch_detail),
    path('programs/', RedirectView.as_view(pattern_name='program_list', permanent=True, query_string=True)),
    path('programs/<int:branch_id>/', RedirectView.as_view(url='/programs/?branch=%(branch_id)s', permanent=True)),
    path('programs/details/<int:program_id>/', RedirectView.as_view(pattern_name='program_detail', permanent=True)),
]
