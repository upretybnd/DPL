from django.urls import path
from . import views

urlpatterns = [
    path('chapters/', views.branch_details, name='branch_details'),
    path('chapters/<slug:slug>/', views.branch_detail, name='branch_detail'),
    path('about/<slug:slug>/', views.branch_detail, name='about_page'),
    path('programs/', views.program_list, name='program_list'),
    path('programs/<int:program_id>/', views.program_detail, name='program_detail'),
]
