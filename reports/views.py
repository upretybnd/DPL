from django.db import models
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from branches.models import ParentBranch
from .forms import ProjectForm, ProjectReportForm, ReportCommentForm
from .models import (
    BranchRole,
    EvidenceRequirement,
    Project,
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

    if request.method == "POST":
        comment_form = ReportCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.project = project
            comment.author = request.user
            comment.save()
            messages.success(request, "Comment added.")
            return redirect("project_detail", project_id=project.id)
    else:
        comment_form = ReportCommentForm()

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
    messages.success(request, "Project submitted for review.")
    return redirect("project_detail", project_id=project.id)


@role_required(BranchRole.ROLE_NATIONAL_ADMIN)
def project_review_action(request, project_id, action):
    if action not in {"approve", "reject"}:
        messages.error(request, "Invalid review action.")
        return redirect("project_detail", project_id=project_id)

    project = get_object_or_404(Project, id=project_id)
    if project.status not in [Project.STATUS_SUBMITTED, Project.STATUS_REVIEWED]:
        messages.warning(request, "Project is not in a reviewable state.")
        return redirect("project_detail", project_id=project.id)

    next_status = Project.STATUS_APPROVED if action == "approve" else Project.STATUS_REJECTED
    prev_status = project.status
    project.status = next_status
    project.is_published = action == "approve"
    project.save(update_fields=["status", "is_published", "updated_at"])

    report, _ = ProjectReport.objects.get_or_create(project=project)
    now = timezone.now()
    if action == "approve":
        report.approved_at = now
    else:
        report.reviewed_at = now
    report.save(update_fields=["approved_at", "reviewed_at"])

    ReportStatusHistory.objects.create(
        project=project,
        from_status=prev_status,
        to_status=next_status,
        changed_by=request.user,
        note=f"Action: {action}",
    )

    messages.success(request, f"Project {action}d successfully.")
    return redirect("project_detail", project_id=project.id)


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
    messages.success(request, f"Period {period_text} is now {state}.")
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
    y = 800
    lines = [
        f"Project: {project.title}",
        f"Branch: {project.branch.name}",
        f"Type: {project.project_type}",
        f"Date: {project.event_date}",
        f"Status: {project.get_status_display()}",
        f"Beneficiaries: {project.beneficiaries_count}",
        f"Volunteer Hours: {project.volunteer_hours}",
        f"Budget Planned/Actual: {project.budget_planned} / {project.budget_actual}",
        f"Report Period: {report.report_period if report else 'N/A'}",
        "",
        "Impact Summary:",
        project.impact_summary,
    ]
    for line in lines:
        pdf.drawString(40, y, str(line)[:120])
        y -= 20
        if y < 40:
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
    y = 800
    pdf.drawString(40, y, f"Monthly Branch Report - {branch.name} ({period_text})")
    y -= 30
    if not projects.exists():
        pdf.drawString(40, y, "No projects found for this month.")
    else:
        for project in projects:
            row = f"- {project.title} | {project.get_status_display()} | Beneficiaries: {project.beneficiaries_count}"
            pdf.drawString(40, y, row[:120])
            y -= 18
            if y < 40:
                pdf.showPage()
                y = 800
    pdf.save()
    return response
