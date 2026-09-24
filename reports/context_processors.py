from .models import Notification
from .permissions import administered_branches, user_has_portal_access, user_is_national_admin


def report_nav(request):
    """Header data for signed-in users: unread notification count and whether to show the dashboard link."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    return {
        "unread_notification_count": Notification.objects.filter(user=user, is_read=False).count(),
        "has_report_access": user_has_portal_access(user),
        "is_national_admin": user_is_national_admin(user),
        "is_branch_admin": administered_branches(user).exists(),
    }
