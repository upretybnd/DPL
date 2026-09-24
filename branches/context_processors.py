from .models import ParentBranch


def navigation(request):
    """Boards and chapters for the site header, read from the database instead of hard-coded IDs."""
    return {
        "nav_boards": ParentBranch.objects.boards().only("name", "slug"),
        "nav_chapters": ParentBranch.objects.chapters().only("name", "slug"),
        "nav_about": ParentBranch.objects.about_menu().only("name", "slug", "branch_type", "tagline"),
    }
