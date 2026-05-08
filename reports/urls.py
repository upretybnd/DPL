from django.urls import path

from . import views

urlpatterns = [
    path("", views.report_home, name="report_home"),
    path("dashboard/branch/", views.branch_dashboard, name="branch_dashboard"),
    path("dashboard/national/", views.national_dashboard, name="national_dashboard"),
    path("dashboard/national/toggle-period-lock/", views.toggle_reporting_period_lock, name="toggle_reporting_period_lock"),
    path("projects/new/", views.project_create, name="project_create"),
    path("projects/<int:project_id>/", views.project_detail, name="project_detail"),
    path("projects/<int:project_id>/submit/", views.project_submit, name="project_submit"),
    path("projects/<int:project_id>/export/pdf/", views.project_export_pdf, name="project_export_pdf"),
    path("branches/<int:branch_id>/export/monthly/pdf/", views.branch_monthly_export_pdf, name="branch_monthly_export_pdf"),
    path("projects/<int:project_id>/<str:action>/", views.project_review_action, name="project_review_action"),
]
