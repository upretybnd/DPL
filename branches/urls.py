# branches/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('branches/', views.branch_details, name='branch_details'),  # List of all branches
    path('branch/<int:branch_id>/', views.branch_detail, name='branch_detail'),  # Detail of a specific branch
    path('programs/', views.program_list, name='program_list'),
    path('programs/<int:branch_id>/', views.program_list, name='branch_program_list'),
    path('programs/details/<int:program_id>/', views.program_detail, name='program_detail'),
]
