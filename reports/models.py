from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from branches.models import ParentBranch
from dpl.storage import private_storage


class BranchRole(models.Model):
    ROLE_NATIONAL_ADMIN = "national_admin"
    ROLE_BRANCH_ADMIN = "branch_admin"
    ROLE_REPORTER = "reporter"
    ROLE_VIEWER = "viewer"

    ROLE_CHOICES = [
        (ROLE_NATIONAL_ADMIN, "National Admin"),
        (ROLE_BRANCH_ADMIN, "Branch Admin"),
        (ROLE_REPORTER, "Reporter"),
        (ROLE_VIEWER, "Viewer"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="branch_roles")
    branch = models.ForeignKey(
        ParentBranch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="user_roles",
        help_text="Keep branch empty only for national admins.",
    )
    role = models.CharField(max_length=32, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "branch", "role")

    def __str__(self):
        branch_name = self.branch.name if self.branch else "All Branches"
        return f"{self.user.username} - {self.get_role_display()} ({branch_name})"


class Project(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_REVIEWED = "reviewed"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_REVIEWED, "Reviewed"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    branch = models.ForeignKey(ParentBranch, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=255)
    project_type = models.CharField(max_length=100)
    sdg_tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated SDG tags")
    event_date = models.DateField(default=timezone.now)
    location = models.CharField(max_length=255, blank=True)
    budget_planned = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    budget_actual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    beneficiaries_count = models.PositiveIntegerField(default=0)
    volunteer_hours = models.PositiveIntegerField(default=0)
    impact_summary = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="projects_created")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-event_date", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def sdg_list(self):
        return [tag.strip() for tag in self.sdg_tags.split(",") if tag.strip()]


class ReportingPeriod(models.Model):
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    is_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("year", "month")
        ordering = ["-year", "-month"]

    def __str__(self):
        state = "Locked" if self.is_locked else "Open"
        return f"{self.year:04d}-{self.month:02d} ({state})"


class ProjectReport(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="report")
    report_period = models.CharField(max_length=20, help_text="Example: 2026-05")
    objectives = models.TextField(blank=True)
    outcomes = models.TextField(blank=True)
    challenges = models.TextField(blank=True)
    lessons_learned = models.TextField(blank=True)
    partner_organizations = models.CharField(max_length=255, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Report - {self.project.title}"


class ProjectEvidence(models.Model):
    EVIDENCE_PHOTO = "photo"
    EVIDENCE_INVOICE = "invoice"
    EVIDENCE_ATTENDANCE = "attendance"
    EVIDENCE_MEDIA_LINK = "media_link"
    EVIDENCE_OTHER = "other"

    EVIDENCE_CHOICES = [
        (EVIDENCE_PHOTO, "Photo"),
        (EVIDENCE_INVOICE, "Invoice"),
        (EVIDENCE_ATTENDANCE, "Attendance"),
        (EVIDENCE_MEDIA_LINK, "Media Link"),
        (EVIDENCE_OTHER, "Other"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="evidences")
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_CHOICES)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="project_evidence/", storage=private_storage, null=True, blank=True)
    external_url = models.URLField(blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_evidence_type_display()} - {self.project.title}"


class EvidenceRequirement(models.Model):
    project_type = models.CharField(max_length=100)
    evidence_type = models.CharField(max_length=20, choices=ProjectEvidence.EVIDENCE_CHOICES)
    is_required = models.BooleanField(default=True)

    class Meta:
        unique_together = ("project_type", "evidence_type")
        ordering = ["project_type", "evidence_type"]

    def __str__(self):
        label = "Required" if self.is_required else "Optional"
        return f"{self.project_type} - {self.get_evidence_type_display()} ({label})"


class BeneficiaryStat(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="beneficiary_stats")
    group_name = models.CharField(max_length=100)
    male_count = models.PositiveIntegerField(default=0)
    female_count = models.PositiveIntegerField(default=0)
    other_count = models.PositiveIntegerField(default=0)

    @property
    def total(self):
        return self.male_count + self.female_count + self.other_count

    def __str__(self):
        return f"{self.group_name} - {self.project.title}"


class ReportComment(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    comment = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ReportStatusHistory(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=20, choices=Project.STATUS_CHOICES)
    to_status = models.CharField(max_length=20, choices=Project.STATUS_CHOICES)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    note = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="report_notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.title}"


class AuditLog(models.Model):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=60)
    entity_id = models.PositiveIntegerField()
    branch = models.ForeignKey(ParentBranch, on_delete=models.SET_NULL, null=True, blank=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.action} {self.entity_type}#{self.entity_id}"
