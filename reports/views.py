import json
import csv

from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from branches.models import ParentBranch
from .forms import ProjectEvidenceForm, ProjectForm, ProjectReportForm, ReportCommentForm, ReviewActionForm
from .models import (
    AuditLog,
    BranchRole,
    EvidenceRequirement,
    Notification,
    Project,
    ProjectEvidence,
    ProjectReport,
    ReportingPeriod,
    ReportStatusHistory,
)
from .permissions import (
    can_manage_branch,
    require_branch_manage_access,
    require_branch_view_access,
    role_required,
    user_branch_ids,
    user_is_national_admin,
)


@login_required
def report_home(request):
    if user_is_national_admin(request.user):
        return redirect("national_dashboard")
    return redirect("branch_dashboard")


@login_required
def my_notifications(request):
    page_obj = Paginator(Notification.objects.filter(user=request.user), 25).get_page(request.GET.get("page"))
    return render(request, "reports/my_notifications.html", {"notifications": page_obj})


def _parse_period(period_text):
    try:
        year_text, month_text = period_text.split("-")
        return int(year_text), int(month_text)
    except (ValueError, AttributeError):
        return None, None


def _period_key_for_project(project):
    report = getattr(project, "report", None)
    if report and report.report_period:
        return report.report_period
    return project.event_date.strftime("%Y-%m")


def _draw_wrapped_text(pdf, text, x, y, max_width, line_height=14):
    text = str(text or "")
    words = text.split()
    if not words:
        return y - line_height
    current_line = ""
    for word in words:
        candidate = f"{current_line} {word}".strip()
        if pdf.stringWidth(candidate, "Helvetica", 10) <= max_width:
            current_line = candidate
        else:
            pdf.drawString(x, y, current_line)
            y -= line_height
            current_line = word
    if current_line:
        pdf.drawString(x, y, current_line)
        y -= line_height
    return y


def _log_audit(actor, action, entity_type, entity_id, branch=None, details=""):
    AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        branch=branch,
        details=details[:1500],
    )


def _notify(users, title, message, link=""):
    valid_users = [u for u in users if u and u.is_active]
    notifications = [Notification(user=user, title=title, message=message, link=link) for user in valid_users]
    if notifications:
        Notification.objects.bulk_create(notifications)
    if getattr(settings, "DEFAULT_FROM_EMAIL", "") and valid_users:
        emails = [u.email for u in valid_users if u.email]
        if emails:
            send_mail(
                subject=title,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=emails,
                fail_silently=True,
            )


@role_required(BranchRole.ROLE_VIEWER)
def branch_dashboard(request):
    branch_ids = user_branch_ids(request.user)
    branches = ParentBranch.objects.filter(branch_id__in=branch_ids).order_by("name")

    selected_branch_id = request.GET.get("branch")
    selected_branch = None
    if selected_branch_id:
        selected_branch = get_object_or_404(branches, branch_id=selected_branch_id)
    elif branches.exists():
        selected_branch = branches.first()

    projects = Project.objects.none()
    stats = {"total": 0, "submitted": 0, "approved": 0, "beneficiaries": 0, "volunteer_hours": 0}
    if selected_branch:
        require_branch_view_access(request.user, selected_branch)
        projects = Project.objects.filter(branch=selected_branch)
        stats = projects.aggregate(
            total=Count("id"),
            submitted=Count("id", filter=models.Q(status=Project.STATUS_SUBMITTED)),
            approved=Count("id", filter=models.Q(status=Project.STATUS_APPROVED)),
            beneficiaries=Sum("beneficiaries_count"),
            volunteer_hours=Sum("volunteer_hours"),
        )
        for key, value in stats.items():
            stats[key] = value or 0

    return render(
        request,
        "reports/branch_dashboard.html",
        {
            "branches": branches,
            "selected_branch": selected_branch,
            "projects": projects[:10],
            "stats": stats,
            "current_period": timezone.now().strftime("%Y-%m"),
        },
    )


@role_required(BranchRole.ROLE_NATIONAL_ADMIN)
def national_dashboard(request):
    branch_rows = (
        ParentBranch.objects.annotate(
            total_projects=Count("projects"),
            approved_projects=Count("projects", filter=models.Q(projects__status=Project.STATUS_APPROVED)),
            total_beneficiaries=Sum("projects__beneficiaries_count"),
            total_hours=Sum("projects__volunteer_hours"),
        )
        .order_by("name")
    )

    recent_projects = Project.objects.select_related("branch", "created_by")[:12]
    return render(
        request,
        "reports/national_dashboard.html",
        {
            "branch_rows": branch_rows,
            "recent_projects": recent_projects,
            "periods": ReportingPeriod.objects.all()[:12],
            "current_period": timezone.now().strftime("%Y-%m"),
        },
    )


@role_required(BranchRole.ROLE_NATIONAL_ADMIN)
def national_analytics(request):
    trend_rows = (
        Project.objects.annotate(period=TruncMonth("event_date"))
        .values("period")
        .annotate(
            total_projects=Count("id"),
            approved_projects=Count("id", filter=models.Q(status=Project.STATUS_APPROVED)),
            beneficiaries=Sum("beneficiaries_count"),
        )
        .order_by("period")
    )
    trend_labels = [row["period"].strftime("%Y-%m") for row in trend_rows if row["period"]]
    trend_totals = [row["total_projects"] or 0 for row in trend_rows]
    trend_approved = [row["approved_projects"] or 0 for row in trend_rows]
    trend_beneficiaries = [row["beneficiaries"] or 0 for row in trend_rows]

    branch_rankings = (
        ParentBranch.objects.annotate(
            total_projects=Count("projects"),
            approved_projects=Count("projects", filter=models.Q(projects__status=Project.STATUS_APPROVED)),
            total_beneficiaries=Sum("projects__beneficiaries_count"),
            total_hours=Sum("projects__volunteer_hours"),
        )
        .order_by("-total_beneficiaries", "-approved_projects", "name")
    )

    sdg_counter = {}
    for raw_tags in Project.objects.exclude(sdg_tags="").values_list("sdg_tags", flat=True):
        tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
        for tag in tags:
            key = tag.upper()
            sdg_counter[key] = sdg_counter.get(key, 0) + 1
    sdg_distribution = sorted(
        [{"label": key, "count": count} for key, count in sdg_counter.items()],
        key=lambda item: (-item["count"], item["label"]),
    )

    return render(
        request,
        "reports/national_analytics.html",
        {
            "trend_labels_json": json.dumps(trend_labels),
            "trend_totals_json": json.dumps(trend_totals),
            "trend_approved_json": json.dumps(trend_approved),
            "trend_beneficiaries_json": json.dumps(trend_beneficiaries),
            "branch_rankings": branch_rankings,
            "sdg_distribution": sdg_distribution,
            "sdg_labels_json": json.dumps([row["label"] for row in sdg_distribution[:12]]),
            "sdg_counts_json": json.dumps([row["count"] for row in sdg_distribution[:12]]),
        },
    )


@role_required(BranchRole.ROLE_NATIONAL_ADMIN)
def national_analytics_export_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="national_analytics.csv"'
    writer = csv.writer(response)
    writer.writerow(["Branch", "Total Projects", "Approved Projects", "Beneficiaries", "Volunteer Hours"])
    rows = (
        ParentBranch.objects.annotate(
            total_projects=Count("projects"),
            approved_projects=Count("projects", filter=models.Q(projects__status=Project.STATUS_APPROVED)),
            total_beneficiaries=Sum("projects__beneficiaries_count"),
            total_hours=Sum("projects__volunteer_hours"),
        )
        .order_by("name")
    )
    for row in rows:
        writer.writerow(
            [
                row.name,
                row.total_projects or 0,
                row.approved_projects or 0,
                row.total_beneficiaries or 0,
                row.total_hours or 0,
            ]
        )
    _log_audit(request.user, "analytics_export_csv", "analytics", 0, details="National analytics CSV exported")
    return response


def public_project_list(request):
    published_projects = (
        Project.objects.filter(is_published=True, status=Project.STATUS_APPROVED)
        .select_related("branch")
        .order_by("-event_date", "-id")
    )
    branch = request.GET.get("branch", "").strip()
    year = request.GET.get("year", "").strip()
    month = request.GET.get("month", "").strip()
    sdg = request.GET.get("sdg", "").strip()
    q = request.GET.get("q", "").strip()
    if branch:
        published_projects = published_projects.filter(branch__branch_id=branch)
    if year.isdigit():
        published_projects = published_projects.filter(event_date__year=int(year))
    if month.isdigit():
        published_projects = published_projects.filter(event_date__month=int(month))
    if sdg:
        published_projects = published_projects.filter(sdg_tags__icontains=sdg)
    if q:
        published_projects = published_projects.filter(
            models.Q(title__icontains=q) | models.Q(project_type__icontains=q) | models.Q(impact_summary__icontains=q)
        )
    paginator = Paginator(published_projects, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    public_branches = ParentBranch.objects.filter(
        projects__status=Project.STATUS_APPROVED, projects__is_published=True
    ).distinct().order_by("name")
    available_years = (
        Project.objects.filter(is_published=True, status=Project.STATUS_APPROVED)
        .dates("event_date", "year", order="DESC")
    )
    return render(
        request,
        "reports/public_project_list.html",
        {
            "projects": page_obj,
            "q": q,
            "branch": branch,
            "year": year,
            "month": month,
            "sdg": sdg,
            "public_branches": public_branches,
            "available_years": available_years,
            "month_choices": range(1, 13),
        },
    )


def public_project_detail(request, project_id):
    project = get_object_or_404(
        Project.objects.filter(is_published=True, status=Project.STATUS_APPROVED).select_related("branch"),
        id=project_id,
    )
    return render(
        request,
        "reports/public_project_detail.html",
        {
            "project": project,
            "report": getattr(project, "report", None),
            "evidences": project.evidences.all()[:20],
            "beneficiary_stats": project.beneficiary_stats.all()[:20],
        },
    )


@role_required(BranchRole.ROLE_REPORTER)
def project_create(request):
    if request.method == "POST":
        form = ProjectForm(request.POST)
        report_form = ProjectReportForm(request.POST)
        if form.is_valid() and report_form.is_valid():
            project = form.save(commit=False)
            require_branch_manage_access(request.user, project.branch)
            project.created_by = request.user
            project.save()
            report = report_form.save(commit=False)
            report.project = project
            report.save()
            messages.success(request, "Project report draft created.")
            return redirect("project_detail", project_id=project.id)
    else:
        form = ProjectForm()
        report_form = ProjectReportForm(initial={"report_period": timezone.now().strftime("%Y-%m")})

    allowed_branches = user_branch_ids(request.user)
    form.fields["branch"].queryset = ParentBranch.objects.filter(branch_id__in=allowed_branches)

    return render(
        request,
        "reports/project_form.html",
        {
            "form": form,
            "report_form": report_form,
            "mode": "create",
        },
    )


@role_required(BranchRole.ROLE_VIEWER)
def project_detail(request, project_id):
    project = get_object_or_404(Project.objects.select_related("branch", "created_by"), id=project_id)
    require_branch_view_access(request.user, project.branch)

    if request.method == "POST" and request.POST.get("form_type") == "comment":
        comment_form = ReportCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.project = project
            comment.author = request.user
            comment.save()
            _log_audit(request.user, "comment_added", "project", project.id, project.branch, details=comment.comment)
            messages.success(request, "Comment added.")
            return redirect("project_detail", project_id=project.id)
    else:
        comment_form = ReportCommentForm()
    if request.method == "POST" and request.POST.get("form_type") == "evidence":
        evidence_form = ProjectEvidenceForm(request.POST, request.FILES)
        if evidence_form.is_valid():
            require_branch_manage_access(request.user, project.branch)
            evidence = evidence_form.save(commit=False)
            evidence.project = project
            evidence.uploaded_by = request.user
            evidence.save()
            _log_audit(
                request.user,
                "evidence_added",
                "project",
                project.id,
                project.branch,
                details=f"{evidence.evidence_type}: {evidence.title}",
            )
            messages.success(request, "Evidence uploaded.")
            return redirect("project_detail", project_id=project.id)
    else:
        evidence_form = ProjectEvidenceForm()

    return render(
        request,
        "reports/project_detail.html",
        {
            "project": project,
            "report": getattr(project, "report", None),
            "comments": project.comments.select_related("author").all(),
            "history": project.status_history.select_related("changed_by").all(),
            "comment_form": comment_form,
            "can_manage": can_manage_branch(request.user, project.branch),
            "can_review": user_is_national_admin(request.user),
            "evidence_form": evidence_form,
            "evidences": project.evidences.all(),
            "review_form": ReviewActionForm(),
        },
    )


@role_required(BranchRole.ROLE_REPORTER)
def project_submit(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    require_branch_manage_access(request.user, project.branch)

    if project.status != Project.STATUS_DRAFT and project.status != Project.STATUS_REJECTED:
        messages.warning(request, "Only draft or rejected projects can be submitted.")
        return redirect("project_detail", project_id=project.id)

    report, _ = ProjectReport.objects.get_or_create(project=project)
    year, month = _parse_period(report.report_period)
    if not year or not month:
        messages.error(request, "Invalid report period format. Use YYYY-MM.")
        return redirect("project_detail", project_id=project.id)

    period = ReportingPeriod.objects.filter(year=year, month=month).first()
    if period and period.is_locked:
        messages.error(request, f"Reporting period {report.report_period} is locked.")
        return redirect("project_detail", project_id=project.id)

    required_types = list(
        EvidenceRequirement.objects.filter(
            project_type__iexact=project.project_type, is_required=True
        ).values_list("evidence_type", flat=True)
    )
    if not required_types:
        required_types = ["photo"]
    existing_types = set(project.evidences.values_list("evidence_type", flat=True))
    missing = [e for e in required_types if e not in existing_types]
    if missing:
        messages.error(
            request,
            f"Missing required evidence types: {', '.join(missing)}.",
        )
        return redirect("project_detail", project_id=project.id)

    prev_status = project.status
    project.status = Project.STATUS_SUBMITTED
    project.save(update_fields=["status", "updated_at"])

    report.submitted_at = timezone.now()
    report.save(update_fields=["submitted_at"])

    ReportStatusHistory.objects.create(
        project=project,
        from_status=prev_status,
        to_status=Project.STATUS_SUBMITTED,
        changed_by=request.user,
        note="Submitted for review",
    )
    _log_audit(request.user, "project_submitted", "project", project.id, project.branch, details="Submitted for review")
    national_admin_users = [
        role.user
        for role in BranchRole.objects.select_related("user").filter(
            role=BranchRole.ROLE_NATIONAL_ADMIN, is_active=True
        )
    ]
    _notify(
        national_admin_users,
        "Project submitted for review",
        f"{project.title} from {project.branch.name} was submitted.",
        link=f"/reports/projects/{project.id}/",
    )
    messages.success(request, "Project submitted for review.")
    return redirect("project_detail", project_id=project.id)


@role_required(BranchRole.ROLE_NATIONAL_ADMIN)
def project_review_action(request, project_id, action):
    if action not in {"review", "approve", "reject"}:
        messages.error(request, "Invalid review action.")
        return redirect("project_detail", project_id=project_id)

    project = get_object_or_404(Project, id=project_id)
    if project.status not in [Project.STATUS_SUBMITTED, Project.STATUS_REVIEWED]:
        messages.warning(request, "Project is not in a reviewable state.")
        return redirect("project_detail", project_id=project.id)
    review_note = ReviewActionForm(request.POST).data.get("note", "").strip() if request.method == "POST" else ""
    if action == "review":
        next_status = Project.STATUS_REVIEWED
    else:
        next_status = Project.STATUS_APPROVED if action == "approve" else Project.STATUS_REJECTED
    prev_status = project.status
    project.status = next_status
    project.is_published = action == "approve"
    project.save(update_fields=["status", "is_published", "updated_at"])

    report, _ = ProjectReport.objects.get_or_create(project=project)
    now = timezone.now()
    if action == "approve":
        report.approved_at = now
        report.reviewed_at = now
    elif action == "review":
        report.reviewed_at = now
    report.save(update_fields=["approved_at", "reviewed_at"])

    ReportStatusHistory.objects.create(
        project=project,
        from_status=prev_status,
        to_status=next_status,
        changed_by=request.user,
        note=f"Action: {action}. {review_note}",
    )
    _log_audit(
        request.user,
        f"project_{action}",
        "project",
        project.id,
        project.branch,
        details=review_note or f"Project {action}ed",
    )
    recipients = [project.created_by] if project.created_by else []
    _notify(
        recipients,
        f"Project {action} update",
        f"{project.title} is now {project.get_status_display()}.",
        link=f"/reports/projects/{project.id}/",
    )
    messages.success(request, f"Project {action}ed successfully.")
    return redirect("project_detail", project_id=project.id)


@role_required(BranchRole.ROLE_REPORTER)
def evidence_delete(request, evidence_id):
    evidence = get_object_or_404(ProjectEvidence.objects.select_related("project__branch"), id=evidence_id)
    require_branch_manage_access(request.user, evidence.project.branch)
    project_id = evidence.project_id
    details = f"{evidence.evidence_type}: {evidence.title}"
    evidence.delete()
    _log_audit(request.user, "evidence_deleted", "project", project_id, evidence.project.branch, details=details)
    messages.success(request, "Evidence deleted.")
    return redirect("project_detail", project_id=project_id)


@role_required(BranchRole.ROLE_NATIONAL_ADMIN)
def toggle_reporting_period_lock(request):
    period_text = request.GET.get("period")
    year, month = _parse_period(period_text)
    if not year or not month:
        messages.error(request, "Invalid period format. Use YYYY-MM.")
        return redirect("national_dashboard")

    period, _ = ReportingPeriod.objects.get_or_create(year=year, month=month)
    period.is_locked = not period.is_locked
    period.locked_at = timezone.now() if period.is_locked else None
    period.save(update_fields=["is_locked", "locked_at"])
    state = "locked" if period.is_locked else "unlocked"
    recipient_users = list(
        {
            role.user_id: role.user
            for role in BranchRole.objects.select_related("user").filter(
                role__in=[BranchRole.ROLE_BRANCH_ADMIN, BranchRole.ROLE_REPORTER], is_active=True
            )
        }.values()
    )
    _notify(
        recipient_users,
        f"Reporting period {state}",
        f"Period {period_text} has been {state} by national admin.",
        link="/reports/dashboard/branch/",
    )
    _log_audit(
        request.user,
        f"period_{state}",
        "reporting_period",
        period.id,
        details=f"{period.year:04d}-{period.month:02d}",
    )
    messages.success(request, f"Period {period_text} is now {state}.")
    return redirect("national_dashboard")


@role_required(BranchRole.ROLE_NATIONAL_ADMIN)
def send_submission_reminders(request):
    period_text = request.GET.get("period", timezone.now().strftime("%Y-%m"))
    year, month = _parse_period(period_text)
    if not year or not month:
        messages.error(request, "Invalid period format. Use YYYY-MM.")
        return redirect("national_dashboard")
    target_projects = Project.objects.filter(
        event_date__year=year,
        event_date__month=month,
        status__in=[Project.STATUS_DRAFT, Project.STATUS_REJECTED],
    ).select_related("created_by", "branch")
    reminder_count = 0
    for project in target_projects:
        required_types = list(
            EvidenceRequirement.objects.filter(
                project_type__iexact=project.project_type, is_required=True
            ).values_list("evidence_type", flat=True)
        ) or ["photo"]
        existing_types = set(project.evidences.values_list("evidence_type", flat=True))
        missing = [e for e in required_types if e not in existing_types]
        if not missing:
            continue
        recipients = [project.created_by] if project.created_by else []
        _notify(
            recipients,
            "Reporting reminder: missing evidence",
            f"{project.title} is missing: {', '.join(missing)} for period {period_text}.",
            link=f"/reports/projects/{project.id}/",
        )
        reminder_count += 1
    _log_audit(
        request.user,
        "submission_reminders_sent",
        "reporting_period",
        0,
        details=f"{reminder_count} reminders for {period_text}",
    )
    messages.success(request, f"Sent {reminder_count} reminder(s) for {period_text}.")
    return redirect("national_dashboard")


@role_required(BranchRole.ROLE_VIEWER)
def project_export_pdf(request, project_id):
    project = get_object_or_404(Project.objects.select_related("branch", "created_by"), id=project_id)
    require_branch_view_access(request.user, project.branch)
    report = getattr(project, "report", None)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        return HttpResponse(
            "PDF export requires reportlab. Install it to enable this feature.",
            content_type="text/plain",
            status=501,
        )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="project_{project.id}.pdf"'
    pdf = canvas.Canvas(response, pagesize=A4)
    y = 805
    left = 40
    content_width = 515

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(left, y, "Dynamic Public Library")
    y -= 18
    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, y, "Project Report")
    y -= 22
    pdf.line(left, y, left + content_width, y)
    y -= 20

    metadata_rows = [
        ("Project", project.title),
        ("Branch", project.branch.name),
        ("Project Type", project.project_type),
        ("Report Period", report.report_period if report else "N/A"),
        ("Event Date", project.event_date),
        ("Status", project.get_status_display()),
    ]
    pdf.setFont("Helvetica", 10)
    for label, value in metadata_rows:
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left, y, f"{label}:")
        pdf.setFont("Helvetica", 10)
        y = _draw_wrapped_text(pdf, value, left + 95, y, content_width - 95)
        if y < 90:
            pdf.showPage()
            y = 800

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(left, y, "Financials and Reach")
    y -= 16
    pdf.setFont("Helvetica", 10)
    y = _draw_wrapped_text(
        pdf,
        f"Budget planned: {project.budget_planned} | Budget actual: {project.budget_actual}",
        left,
        y,
        content_width,
    )
    y = _draw_wrapped_text(
        pdf,
        f"Beneficiaries: {project.beneficiaries_count} | Volunteer hours: {project.volunteer_hours}",
        left,
        y,
        content_width,
    )

    if report:
        sections = [
            ("Objectives", report.objectives),
            ("Outcomes", report.outcomes),
            ("Challenges", report.challenges),
            ("Lessons Learned", report.lessons_learned),
        ]
    else:
        sections = []

    sections.append(("Impact Summary", project.impact_summary))
    for section_title, section_body in sections:
        if y < 110:
            pdf.showPage()
            y = 800
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(left, y, section_title)
        y -= 16
        pdf.setFont("Helvetica", 10)
        y = _draw_wrapped_text(pdf, section_body or "N/A", left, y, content_width)
        y -= 8

    evidence_rows = list(project.evidences.values_list("evidence_type", "title")[:12])
    if evidence_rows:
        if y < 120:
            pdf.showPage()
            y = 800
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(left, y, "Evidence")
        y -= 16
        pdf.setFont("Helvetica", 10)
        for evidence_type, evidence_title in evidence_rows:
            y = _draw_wrapped_text(pdf, f"- {evidence_type}: {evidence_title}", left, y, content_width)
            if y < 70:
                pdf.showPage()
                y = 800

    pdf.save()
    return response


@role_required(BranchRole.ROLE_VIEWER)
def branch_monthly_export_pdf(request, branch_id):
    branch = get_object_or_404(ParentBranch, branch_id=branch_id)
    require_branch_view_access(request.user, branch)
    period_text = request.GET.get("period", timezone.now().strftime("%Y-%m"))
    year, month = _parse_period(period_text)
    if not year or not month:
        return HttpResponse("Invalid period format. Use YYYY-MM.", status=400, content_type="text/plain")

    projects = Project.objects.filter(branch=branch, event_date__year=year, event_date__month=month)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        return HttpResponse(
            "PDF export requires reportlab. Install it to enable this feature.",
            content_type="text/plain",
            status=501,
        )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{branch.name}_{period_text}.pdf"'
    pdf = canvas.Canvas(response, pagesize=A4)
    left = 40
    width = 515
    y = 805
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(left, y, "Dynamic Public Library")
    y -= 18
    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, y, f"Monthly Branch Summary - {branch.name} ({period_text})")
    y -= 22
    pdf.line(left, y, left + width, y)
    y -= 16
    if not projects.exists():
        pdf.setFont("Helvetica", 10)
        pdf.drawString(left, y, "No projects found for this month.")
    else:
        totals = projects.aggregate(
            total_projects=Count("id"),
            total_beneficiaries=Sum("beneficiaries_count"),
            total_hours=Sum("volunteer_hours"),
            total_budget=Sum("budget_actual"),
        )
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(left, y, "Totals")
        y -= 16
        pdf.setFont("Helvetica", 10)
        summary_line = (
            f"Projects: {totals['total_projects'] or 0} | Beneficiaries: {totals['total_beneficiaries'] or 0} | "
            f"Volunteer hours: {totals['total_hours'] or 0} | Budget actual: {totals['total_budget'] or 0}"
        )
        y = _draw_wrapped_text(pdf, summary_line, left, y, width)
        y -= 8
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(left, y, "Projects")
        y -= 16
        pdf.setFont("Helvetica", 10)
        for project in projects:
            row = (
                f"- {project.title} ({project.project_type}) | Status: {project.get_status_display()} | "
                f"Beneficiaries: {project.beneficiaries_count} | Hours: {project.volunteer_hours}"
            )
            y = _draw_wrapped_text(pdf, row, left, y, width)
            if y < 65:
                pdf.showPage()
                y = 800
    pdf.save()
    _log_audit(
        request.user,
        "branch_pdf_export",
        "branch",
        branch.branch_id,
        branch=branch,
        details=f"Monthly PDF exported for {period_text}",
    )
    return response


@role_required(BranchRole.ROLE_NATIONAL_ADMIN)
def audit_log_list(request):
    logs = AuditLog.objects.select_related("actor", "branch")
    action = request.GET.get("action", "").strip()
    if action:
        logs = logs.filter(action__icontains=action)
    paginator = Paginator(logs, 40)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "reports/audit_log_list.html", {"logs": page_obj, "action": action})


@role_required(BranchRole.ROLE_NATIONAL_ADMIN)
def audit_log_export_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="audit_log.csv"'
    writer = csv.writer(response)
    writer.writerow(["When", "Actor", "Action", "Entity", "Entity ID", "Branch", "Details"])
    for row in AuditLog.objects.select_related("actor", "branch").all()[:5000]:
        writer.writerow(
            [
                row.created_at,
                row.actor.username if row.actor else "System",
                row.action,
                row.entity_type,
                row.entity_id,
                row.branch.name if row.branch else "",
                row.details,
            ]
        )
    _log_audit(request.user, "audit_export_csv", "audit", 0, details="Audit CSV exported")
    return response
