from django.contrib import admin

from .models import (
    AuditLog,
    BeneficiaryStat,
    BranchRole,
    EvidenceRequirement,
    Notification,
    Project,
    ProjectEvidence,
    ProjectReport,
    ReportingPeriod,
    ReportComment,
    ReportStatusHistory,
)


@admin.register(BranchRole)
class BranchRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "branch", "role", "is_active")
    list_filter = ("role", "is_active", "branch")
    search_fields = ("user__username", "user__email", "branch__name")


class ProjectEvidenceInline(admin.TabularInline):
    model = ProjectEvidence
    extra = 0


class BeneficiaryStatInline(admin.TabularInline):
    model = BeneficiaryStat
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "branch", "project_type", "status", "event_date", "created_by")
    list_filter = ("status", "branch", "project_type")
    search_fields = ("title", "impact_summary", "branch__name")
    inlines = [ProjectEvidenceInline, BeneficiaryStatInline]


@admin.register(ProjectReport)
class ProjectReportAdmin(admin.ModelAdmin):
    list_display = ("project", "report_period", "submitted_at", "reviewed_at", "approved_at")


@admin.register(ProjectEvidence)
class ProjectEvidenceAdmin(admin.ModelAdmin):
    list_display = ("project", "evidence_type", "title", "uploaded_by", "uploaded_at")


@admin.register(BeneficiaryStat)
class BeneficiaryStatAdmin(admin.ModelAdmin):
    list_display = ("project", "group_name", "male_count", "female_count", "other_count")


@admin.register(ReportComment)
class ReportCommentAdmin(admin.ModelAdmin):
    list_display = ("project", "author", "is_internal", "created_at")


@admin.register(ReportStatusHistory)
class ReportStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("project", "from_status", "to_status", "changed_by", "changed_at")


@admin.register(ReportingPeriod)
class ReportingPeriodAdmin(admin.ModelAdmin):
    list_display = ("year", "month", "is_locked", "locked_at")
    list_filter = ("is_locked", "year")
    search_fields = ("year", "month")


@admin.register(EvidenceRequirement)
class EvidenceRequirementAdmin(admin.ModelAdmin):
    list_display = ("project_type", "evidence_type", "is_required")
    list_filter = ("project_type", "evidence_type", "is_required")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__username", "title", "message")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "entity_type", "entity_id", "actor", "branch", "created_at")
    list_filter = ("action", "entity_type", "branch", "created_at")
    search_fields = ("details", "actor__username")
