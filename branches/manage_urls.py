from django.urls import path

from . import manage

urlpatterns = [
    path('branches/', manage.branch_list, name='mis_branches'),
    path('branches/new/', manage.branch_create, name='mis_branch_create'),
    path('branches/<int:branch_id>/', manage.branch_profile, name='mis_branch_profile'),
    path('branches/<int:branch_id>/team/', manage.team, name='mis_branch_team'),
    path('branches/<int:branch_id>/team/<int:member_id>/', manage.team_edit, name='mis_team_edit'),
    path('branches/<int:branch_id>/team/<int:member_id>/delete/', manage.team_delete, name='mis_team_delete'),
    path('branches/<int:branch_id>/gallery/', manage.gallery, name='mis_branch_gallery'),
    path('branches/<int:branch_id>/gallery/<int:photo_id>/delete/', manage.gallery_delete, name='mis_gallery_delete'),
    path('branches/<int:branch_id>/programs/', manage.programs, name='mis_branch_programs'),
    path('branches/<int:branch_id>/programs/new/', manage.program_form, name='mis_program_create'),
    path('branches/<int:branch_id>/programs/<int:program_id>/', manage.program_form, name='mis_program_edit'),
    path('branches/<int:branch_id>/programs/<int:program_id>/delete/', manage.program_delete, name='mis_program_delete'),
    path('branches/<int:branch_id>/programs/<int:program_id>/photos/<int:photo_id>/delete/', manage.program_photo_delete, name='mis_program_photo_delete'),
    path('branches/<int:branch_id>/members/', manage.members, name='mis_branch_members'),
    path('branches/<int:branch_id>/members/<int:role_id>/remove/', manage.member_remove, name='mis_member_remove'),
    path('national-admins/', manage.national_admins, name='mis_national_admins'),
]
