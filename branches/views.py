import calendar
from urllib.parse import urlencode

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render

from reports.models import Project
from .models import BranchTeam, ParentBranch, Program


def branch_detail(request, slug):
    branch = get_object_or_404(
        ParentBranch.objects.active().select_related("parent").prefetch_related(
            Prefetch("wings", queryset=ParentBranch.objects.active()),
        ),
        slug=slug,
    )
    # Organisations live under /about/, everything else under /chapters/; keep one canonical URL.
    if request.path != branch.get_absolute_url():
        return redirect(branch, permanent=True)
    team = list(branch.branch_teams.all())
    context = {
        "branch": branch,
        "board_members": [m for m in team if m.member_type == BranchTeam.TYPE_BOARD],
        "charter_presidents": [m for m in team if m.member_type == BranchTeam.TYPE_CHARTER_PRESIDENT],
        "past_presidents": [m for m in team if m.member_type == BranchTeam.TYPE_PAST_PRESIDENT],
        "advisors": [m for m in team if m.member_type == BranchTeam.TYPE_ADVISOR],
        "programs": branch.programs.order_by("-program_date")[:6],
        "program_count": branch.programs.count(),
        "projects": Project.objects.filter(
            branch=branch, is_published=True, status=Project.STATUS_APPROVED
        ).order_by("-event_date")[:6],
        "gallery": branch.gallery.all()[:12],
    }
    return render(request, "branches/branch_detail.html", context)


def legacy_branch_detail(request, branch_id):
    """Old /branch/branch/<id>/ links (bookmarks, search results) move permanently to the slug URL."""
    branch = get_object_or_404(ParentBranch, branch_id=branch_id)
    return redirect(branch, permanent=True)


def branch_details(request):
    chapters = (
        ParentBranch.objects.chapters()
        .prefetch_related(Prefetch("wings", queryset=ParentBranch.objects.active()))
        .annotate(program_total=Count("programs", distinct=True))
    )
    province = request.GET.get("province", "").strip()
    q = request.GET.get("q", "").strip()
    if province:
        chapters = chapters.filter(province=province)
    if q:
        chapters = chapters.filter(Q(name__icontains=q) | Q(district__icontains=q) | Q(address__icontains=q))

    return render(request, "branches/branch_details.html", {
        "chapters": chapters,
        "boards": ParentBranch.objects.boards(),
        "province_choices": ParentBranch.PROVINCE_CHOICES,
        "selected_province": province,
        "q": q,
    })


def program_list(request):
    programs = Program.objects.select_related('branch').order_by('-program_date', '-id')

    branch = request.GET.get('branch', '').strip()
    coordinator = request.GET.get('coordinator', '').strip()
    program_date = request.GET.get('program_date', '').strip()
    year = request.GET.get('year', '').strip()
    month = request.GET.get('month', '').strip()

    # Every filter the visitor fills in narrows the results (AND), rather than widening them.
    if branch.isdigit():
        programs = programs.filter(branch__branch_id=int(branch))
    if coordinator:
        programs = programs.filter(coordinator_name__icontains=coordinator)
    if program_date:
        try:
            programs = programs.filter(program_date=program_date)
        except ValidationError:
            pass
    if year.isdigit():
        programs = programs.filter(program_date__year=int(year))
    if month.isdigit() and 1 <= int(month) <= 12:
        programs = programs.filter(program_date__month=int(month))

    paginator = Paginator(programs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'programs/program_list.html', {
        'page_obj': page_obj,
        'branches': ParentBranch.objects.active().order_by('name'),
        'selected_branch': branch,
        'selected_coordinator': coordinator,
        'selected_year': year,
        'selected_month': month,
        'months': [(i, calendar.month_name[i]) for i in range(1, 13)],
        'filter_query': urlencode({k: v for k, v in {
            'branch': branch, 'coordinator': coordinator, 'year': year, 'month': month,
        }.items() if v}),
    })


def program_detail(request, program_id):
    # Get the program by its ID
    program = get_object_or_404(Program, id=program_id)

    # Fetch all the sub-images related to this program
    sub_images = program.sub_images.all()  # Get all sub-images for this program

    # Fetch related programs from the same branch, excluding the current program
    related_programs = Program.objects.filter(branch=program.branch).exclude(id=program_id).order_by('-program_date')[:6]

    # Return the response with the program, sub_images, and related programs
    return render(request, 'programs/program_detail.html', {
        'program': program,
        'related_programs': related_programs,
        'sub_images': sub_images,  # Pass sub-images to the template
    })
