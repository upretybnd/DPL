from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from branches.models import ParentBranch
from .models import BranchRole


ROLE_PRIORITY = {
    BranchRole.ROLE_NATIONAL_ADMIN: 4,
    BranchRole.ROLE_BRANCH_ADMIN: 3,
    BranchRole.ROLE_REPORTER: 2,
    BranchRole.ROLE_VIEWER: 1,
}


def get_user_roles(user):
    if not user.is_authenticated:
        return BranchRole.objects.none()
    if user.is_superuser:
        return BranchRole.objects.filter(role=BranchRole.ROLE_NATIONAL_ADMIN, is_active=True)
    return BranchRole.objects.filter(user=user, is_active=True)


def user_is_national_admin(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return BranchRole.objects.filter(
        user=user,
        role=BranchRole.ROLE_NATIONAL_ADMIN,
        is_active=True,
    ).exists()


def user_branch_ids(user):
    if user_is_national_admin(user):
        return list(ParentBranch.objects.values_list("branch_id", flat=True))
    return list(
        BranchRole.objects.filter(user=user, is_active=True, branch__isnull=False)
        .values_list("branch__branch_id", flat=True)
        .distinct()
    )


def can_manage_branch(user, branch):
    if user_is_national_admin(user):
        return True
    return BranchRole.objects.filter(
        user=user,
        branch=branch,
        role__in=[BranchRole.ROLE_BRANCH_ADMIN, BranchRole.ROLE_REPORTER],
        is_active=True,
    ).exists()


def can_view_branch(user, branch):
    if user_is_national_admin(user):
        return True
    return BranchRole.objects.filter(user=user, branch=branch, is_active=True).exists()


def require_branch_view_access(user, branch):
    if not can_view_branch(user, branch):
        raise PermissionDenied("You do not have access to this branch.")


def require_branch_manage_access(user, branch):
    if not can_manage_branch(user, branch):
        raise PermissionDenied("You do not have permission to manage reports for this branch.")


def role_required(min_role):
    def decorator(view_func):
        @login_required
        def _wrapped(request, *args, **kwargs):
            if user_is_national_admin(request.user):
                return view_func(request, *args, **kwargs)

            min_priority = ROLE_PRIORITY[min_role]
            roles = BranchRole.objects.filter(user=request.user, is_active=True).values_list("role", flat=True)
            has_access = any(ROLE_PRIORITY.get(role, 0) >= min_priority for role in roles)
            if not has_access:
                raise PermissionDenied("You do not have enough privileges.")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
