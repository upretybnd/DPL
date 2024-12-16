from django.core.paginator import Paginator
from django.db.models import Q
from .models import ParentBranch , Program
from django.shortcuts import render, get_object_or_404


def branch_detail(request, branch_id):
    # Retrieve the branch or raise 404 if not found
    branch = get_object_or_404(ParentBranch, branch_id=branch_id)

    # Define a dictionary to map branch_ids to templates
    branch_templates = {
        1: 'branches/biratnagar_teens.html',
        2: 'branches/birtamode.html',
        5: 'branches/guardain_board.html',
        6: 'branches/national_board.html',
    }

    # Use the branch_id to select the template, default to 'branch_details.html'
    template = branch_templates.get(branch_id, 'branches/branch_details.html')

    # Render the appropriate template
    return render(request, template, {'branch': branch})


def branch_details(request):
    branches = ParentBranch.objects.all()  # Fetch all branches
    return render(request, 'branches/branch_details.html', {'branches': branches})


def program_list(request, branch_id=None):
    # Initialize the queryset
    programs = Program.objects.all()

    # Extract filter parameters from the GET request
    branch = request.GET.get('branch')
    coordinator = request.GET.get('coordinator')
    program_date = request.GET.get('program_date')
    year = request.GET.get('year')
    month = request.GET.get('month')

    # Create Q objects for OR filtering
    filters = Q()

    if branch:
        filters |= Q(branch__branch_id=branch)  # OR condition for branch
    if coordinator:
        filters |= Q(coordinator_name__icontains=coordinator)  # OR condition for coordinator
    if program_date:
        filters |= Q(program_date=program_date)  # OR condition for program_date
    if year:
        filters |= Q(program_date__year=year)  # OR condition for year
    if month:
        filters |= Q(program_date__month=month)  # OR condition for month

    # Apply the filters using OR logic
    programs = programs.filter(filters)

    # Set up pagination: 10 programs per page
    paginator = Paginator(programs, 10)  # Show 10 programs per page
    page_number = request.GET.get('page')  # Get the current page number from the URL
    page_obj = paginator.get_page(page_number)  # Get the programs for the current page

    # Get all branches for filter dropdown
    branches = ParentBranch.objects.all()

    return render(request, 'programs/program_list.html', {
        'page_obj': page_obj,
        'branches': branches,
        'selected_branch': branch,
        'selected_coordinator': coordinator,
        'selected_year': year,
        'selected_month': month,
    })






def program_detail(request, program_id):
    # Get the program by its ID
    program = get_object_or_404(Program, id=program_id)

    # Fetch all the sub-images related to this program
    sub_images = program.sub_images.all()  # Get all sub-images for this program

    # Fetch related programs from the same branch, excluding the current program
    related_programs = Program.objects.filter(branch=program.branch).exclude(id=program_id)

    # Return the response with the program, sub_images, and related programs
    return render(request, 'programs/program_detail.html', {
        'program': program,
        'related_programs': related_programs,
        'sub_images': sub_images,  # Pass sub-images to the template
    })
