"""DPL MIS branch workspace: everything a Branch Admin manages for their own branch.

National admins can do all of this for every branch, and also create branches and
appoint Branch Admins / National Admins.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.forms import IMAGE_EXTENSIONS, validate_upload
from reports.audit import log_audit
from reports.models import BranchRole
from reports.permissions import (
    administered_branches,
    assignable_roles,
    require_branch_admin,
    user_is_national_admin,
)
from .forms import (
    BranchCreateForm,
    BranchProfileForm,
    GalleryUploadForm,
    MemberAddForm,
    NationalAdminForm,
    ProgramForm,
    TeamMemberForm,
)
from .models import BranchGalleryImage, BranchTeam, ParentBranch, Program, ProgramImage


def _admin_branch(request, branch_id):
    branch = get_object_or_404(ParentBranch, branch_id=branch_id)
    require_branch_admin(request.user, branch)
    return branch


def _render(request, template, branch, tab, **context):
    return render(request, template, {"branch": branch, "tab": tab, **context})


# ---------------------------------------------------------------- branches

@login_required
def branch_list(request):
    branches = administered_branches(request.user).annotate(
        member_total=Count("user_roles", distinct=True),
        program_total=Count("programs", distinct=True),
    ).order_by("branch_type", "display_order", "name")
    if not user_is_national_admin(request.user) and not branches:
        raise PermissionDenied("You are not a Branch Admin of any branch.")
    if len(branches) == 1 and not user_is_national_admin(request.user):
        return redirect("mis_branch_profile", branch_id=branches[0].branch_id)
    return render(request, "mis/branch_list.html", {"branches": branches, "is_national": user_is_national_admin(request.user)})


@login_required
def branch_create(request):
    if not user_is_national_admin(request.user):
        raise PermissionDenied("Only national admins can create branches.")
    form = BranchCreateForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        branch = form.save()
        log_audit(request.user, "branch_created", "branch", branch.branch_id, branch, branch.name)
        messages.success(request, f"{branch.name} created. Next, add its team and a Branch Admin.")
        return redirect("mis_branch_members", branch_id=branch.branch_id)
    return render(request, "mis/branch_create.html", {"form": form})


@login_required
def branch_profile(request, branch_id):
    branch = _admin_branch(request, branch_id)
    form_class = BranchCreateForm if user_is_national_admin(request.user) else BranchProfileForm
    form = form_class(request.POST or None, request.FILES or None, instance=branch)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_audit(request.user, "branch_profile_updated", "branch", branch.branch_id, branch, ", ".join(form.changed_data))
        messages.success(request, "Branch page updated.")
        return redirect("mis_branch_profile", branch_id=branch.branch_id)
    return _render(request, "mis/branch_profile.html", branch, "profile", form=form)


# ---------------------------------------------------------------- team

@login_required
def team(request, branch_id):
    branch = _admin_branch(request, branch_id)
    form = TeamMemberForm(request.POST or None, request.FILES or None, initial={"display_order": branch.branch_teams.count()})
    if request.method == "POST" and form.is_valid():
        member = form.save(commit=False)
        member.branch = branch
        member.save()
        log_audit(request.user, "team_member_added", "branch_team", member.id, branch, member.member_name)
        messages.success(request, f"{member.member_name} added to the team.")
        return redirect("mis_branch_team", branch_id=branch.branch_id)
    return _render(request, "mis/team.html", branch, "team", form=form, members=branch.branch_teams.all())


@login_required
def team_edit(request, branch_id, member_id):
    branch = _admin_branch(request, branch_id)
    member = get_object_or_404(BranchTeam, id=member_id, branch=branch)
    form = TeamMemberForm(request.POST or None, request.FILES or None, instance=member)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_audit(request.user, "team_member_updated", "branch_team", member.id, branch, member.member_name)
        messages.success(request, "Team member updated.")
        return redirect("mis_branch_team", branch_id=branch.branch_id)
    return _render(request, "mis/team_edit.html", branch, "team", form=form, member=member)


@login_required
@require_POST
def team_delete(request, branch_id, member_id):
    branch = _admin_branch(request, branch_id)
    member = get_object_or_404(BranchTeam, id=member_id, branch=branch)
    log_audit(request.user, "team_member_removed", "branch_team", member.id, branch, member.member_name)
    member.delete()
    messages.success(request, f"{member.member_name} removed from the team.")
    return redirect("mis_branch_team", branch_id=branch.branch_id)


# ---------------------------------------------------------------- gallery

@login_required
def gallery(request, branch_id):
    branch = _admin_branch(request, branch_id)
    form = GalleryUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        photo = form.save(commit=False)
        photo.branch = branch
        photo.save()
        log_audit(request.user, "gallery_photo_added", "branch_gallery", photo.id, branch, photo.caption)
        messages.success(request, "Photo added to the gallery.")
        return redirect("mis_branch_gallery", branch_id=branch.branch_id)
    return _render(request, "mis/gallery.html", branch, "gallery", form=form, photos=branch.gallery.all())


@login_required
@require_POST
def gallery_delete(request, branch_id, photo_id):
    branch = _admin_branch(request, branch_id)
    photo = get_object_or_404(BranchGalleryImage, id=photo_id, branch=branch)
    log_audit(request.user, "gallery_photo_removed", "branch_gallery", photo.id, branch, photo.caption)
    photo.delete()
    messages.success(request, "Photo removed.")
    return redirect("mis_branch_gallery", branch_id=branch.branch_id)


# ---------------------------------------------------------------- programs

@login_required
def programs(request, branch_id):
    branch = _admin_branch(request, branch_id)
    items = branch.programs.annotate(photo_total=Count("sub_images")).order_by("-program_date", "-id")
    return _render(request, "mis/programs.html", branch, "programs", programs=items)


def _save_program_photos(request, program):
    saved, rejected = 0, []
    for upload in request.FILES.getlist("photos"):
        try:
            validate_upload(upload, IMAGE_EXTENSIONS)
        except Exception as error:
            rejected.append(f"{upload.name}: {' '.join(getattr(error, 'messages', [str(error)]))}")
            continue
        ProgramImage.objects.create(program=program, image=upload)
        saved += 1
    for problem in rejected:
        messages.warning(request, f"Skipped {problem}")
    return saved


@login_required
def program_form(request, branch_id, program_id=None):
    branch = _admin_branch(request, branch_id)
    program = get_object_or_404(Program, id=program_id, branch=branch) if program_id else None
    form = ProgramForm(request.POST or None, request.FILES or None, instance=program)
    if program is None:
        form.fields["image"].required = True
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        saved.branch = branch
        saved.save()
        photos = _save_program_photos(request, saved)
        log_audit(request.user, "program_updated" if program else "program_created", "program", saved.id, branch, saved.title)
        messages.success(request, f"Program {'updated' if program else 'created'}{f' with {photos} new photo(s)' if photos else ''}.")
        return redirect("mis_program_edit", branch_id=branch.branch_id, program_id=saved.id)
    return _render(request, "mis/program_form.html", branch, "programs", form=form, program=program)


@login_required
@require_POST
def program_delete(request, branch_id, program_id):
    branch = _admin_branch(request, branch_id)
    program = get_object_or_404(Program, id=program_id, branch=branch)
    log_audit(request.user, "program_deleted", "program", program.id, branch, program.title)
    program.delete()
    messages.success(request, f"Program “{program.title}” deleted.")
    return redirect("mis_branch_programs", branch_id=branch.branch_id)


@login_required
@require_POST
def program_photo_delete(request, branch_id, program_id, photo_id):
    branch = _admin_branch(request, branch_id)
    photo = get_object_or_404(ProgramImage, id=photo_id, program__id=program_id, program__branch=branch)
    photo.delete()
    messages.success(request, "Photo removed.")
    return redirect("mis_program_edit", branch_id=branch.branch_id, program_id=program_id)


# ---------------------------------------------------------------- members & roles

@login_required
def members(request, branch_id):
    branch = _admin_branch(request, branch_id)
    choices = assignable_roles(request.user)
    form = MemberAddForm(request.POST or None, role_choices=choices)
    if request.method == "POST" and form.is_valid():
        role = form.cleaned_data["role"]
        membership, created = BranchRole.objects.get_or_create(user=form.user, branch=branch, role=role)
        if not created and not membership.is_active:
            membership.is_active = True
            membership.save(update_fields=["is_active"])
        log_audit(request.user, "role_granted", "branch_role", membership.id, branch, f"{form.user.username}: {role}")
        messages.success(request, f"{form.user.get_full_name() or form.user.username} is now {membership.get_role_display()} of {branch.name}.")
        return redirect("mis_branch_members", branch_id=branch.branch_id)
    roles = branch.user_roles.select_related("user").order_by("-is_active", "role", "user__username")
    return _render(request, "mis/members.html", branch, "members", form=form, roles=roles,
                   assignable=[k for k, _ in choices])


@login_required
@require_POST
def member_remove(request, branch_id, role_id):
    branch = _admin_branch(request, branch_id)
    membership = get_object_or_404(BranchRole, id=role_id, branch=branch)
    if membership.role not in [k for k, _ in assignable_roles(request.user)]:
        raise PermissionDenied("You can't remove this role.")
    if membership.user == request.user and membership.role == BranchRole.ROLE_BRANCH_ADMIN and not user_is_national_admin(request.user):
        messages.error(request, "You can't remove your own Branch Admin role. Ask a national admin.")
        return redirect("mis_branch_members", branch_id=branch.branch_id)
    membership.is_active = False
    membership.save(update_fields=["is_active"])
    log_audit(request.user, "role_revoked", "branch_role", membership.id, branch, f"{membership.user.username}: {membership.role}")
    messages.success(request, f"Access removed for {membership.user.username}.")
    return redirect("mis_branch_members", branch_id=branch.branch_id)


@login_required
def national_admins(request):
    if not user_is_national_admin(request.user):
        raise PermissionDenied("Only national admins can manage national admins.")
    form = NationalAdminForm(request.POST or None)
    if request.method == "POST":
        remove_id = request.POST.get("remove")
        if remove_id:
            role = get_object_or_404(BranchRole, id=remove_id, role=BranchRole.ROLE_NATIONAL_ADMIN)
            if role.user == request.user:
                messages.error(request, "You can't remove your own national admin role.")
            else:
                role.is_active = False
                role.save(update_fields=["is_active"])
                log_audit(request.user, "role_revoked", "branch_role", role.id, details=f"{role.user.username}: national_admin")
                messages.success(request, f"{role.user.username} is no longer a national admin.")
            return redirect("mis_national_admins")
        if form.is_valid():
            role, created = BranchRole.objects.get_or_create(user=form.user, branch=None, role=BranchRole.ROLE_NATIONAL_ADMIN)
            if not role.is_active:
                role.is_active = True
                role.save(update_fields=["is_active"])
            log_audit(request.user, "role_granted", "branch_role", role.id, details=f"{form.user.username}: national_admin")
            messages.success(request, f"{form.user.username} is now a national admin.")
            return redirect("mis_national_admins")
    admins = BranchRole.objects.filter(role=BranchRole.ROLE_NATIONAL_ADMIN, is_active=True).select_related("user")
    return render(request, "mis/national_admins.html", {"form": form, "admins": admins})
