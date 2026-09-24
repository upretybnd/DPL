from django.urls import path

from . import views

urlpatterns = [
    path("", views.report_home, name="report_home"),
    path("notifications/", views.my_notifications, name="my_notifications"),
    path("notifications/read-all/", views.notifications_mark_read, name="notifications_mark_read"),
    path("notifications/<int:notification_id>/open/", views.notification_open, name="notification_open"),
    path("dashboard/branch/", views.branch_dashboard, name="branch_dashboard"),
    path("dashboard/national/", views.national_dashboard, name="national_dashboard"),
    path("dashboard/national/analytics/", views.national_analytics, name="national_analytics"),
    path("dashboard/national/analytics/export/csv/", views.national_analytics_export_csv, name="national_analytics_export_csv"),
    path("dashboard/national/audit-logs/", views.audit_log_list, name="audit_log_list"),
    path("dashboard/national/audit-logs/export/csv/", views.audit_log_export_csv, name="audit_log_export_csv"),
    path("dashboard/national/toggle-period-lock/", views.toggle_reporting_period_lock, name="toggle_reporting_period_lock"),
    path("dashboard/national/send-reminders/", views.send_submission_reminders, name="send_submission_reminders"),
    path("public/projects/", views.public_project_list, name="public_project_list"),
    path("public/projects/<int:project_id>/", views.public_project_detail, name="public_project_detail"),
    path("projects/new/", views.project_create, name="project_create"),
    path("projects/<int:project_id>/", views.project_detail, name="project_detail"),
    path("projects/<int:project_id>/submit/", views.project_submit, name="project_submit"),
    path("projects/<int:project_id>/edit/", views.project_edit, name="project_edit"),
    path("projects/<int:project_id>/delete/", views.project_delete, name="project_delete"),
    path("evidence/<int:evidence_id>/delete/", views.evidence_delete, name="evidence_delete"),
    path("projects/<int:project_id>/export/pdf/", views.project_export_pdf, name="project_export_pdf"),
    path("branches/<int:branch_id>/export/monthly/pdf/", views.branch_monthly_export_pdf, name="branch_monthly_export_pdf"),
    path("projects/<int:project_id>/<str:action>/", views.project_review_action, name="project_review_action"),
]
