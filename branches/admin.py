from django.contrib import admin
from django.db.models import Q
from django.utils.html import format_html

from reports.models import BranchRole
from reports.permissions import user_is_national_admin
from .models import BranchGalleryImage, BranchTeam, ParentBranch, Program, ProgramImage


def admin_branch_ids(user):
    """Branches a staff user may edit in the admin: all for national admins, otherwise the ones they run."""
    if user_is_national_admin(user):
        return None
    return list(
        ParentBranch.objects.filter(
            Q(manager=user)
            | Q(user_roles__user=user, user_roles__role=BranchRole.ROLE_BRANCH_ADMIN, user_roles__is_active=True)
        ).values_list("branch_id", flat=True).distinct()
    )


def _thumb(file_field, size=50):
    if file_field:
        return format_html('<img src="{}" style="width:{}px;height:{}px;object-fit:cover;border-radius:4px" />', file_field.url, size, size)
    return "—"


class BranchScopedAdmin(admin.ModelAdmin):
    """Limits rows and branch choices to the branches the current user manages."""

    branch_lookup = "branch__branch_id__in"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        ids = admin_branch_ids(request.user)
        return qs if ids is None else qs.filter(**{self.branch_lookup: ids})

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name in ("branch", "parent"):
            ids = admin_branch_ids(request.user)
            if ids is not None and db_field.name == "branch":
                kwargs["queryset"] = ParentBranch.objects.filter(branch_id__in=ids)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class BranchTeamInline(admin.TabularInline):
    model = BranchTeam
    extra = 1
    fields = ('member_name', 'designation', 'member_type', 'term', 'member_image', 'display_order')


class BranchGalleryInline(admin.TabularInline):
    model = BranchGalleryImage
    extra = 1
    fields = ('image', 'caption', 'display_order')


@admin.register(ParentBranch)
class ParentBranchAdmin(BranchScopedAdmin):
    branch_lookup = "branch_id__in"
    list_display = ('name', 'branch_type', 'parent', 'district', 'province', 'is_active', 'in_about_menu', 'display_order', 'image_preview')
    list_editable = ('is_active', 'in_about_menu', 'display_order')
    list_filter = ('branch_type', 'in_about_menu', 'province', 'is_active')
    search_fields = ('name', 'district', 'address')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [BranchTeamInline, BranchGalleryInline]
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'branch_type', 'parent', 'is_active', 'in_about_menu', 'display_order')}),
        ('Public profile', {'fields': ('tagline', 'description', 'main_image', 'established_date')}),
        ('Location & contact', {'fields': ('address', 'district', 'province', 'map_url', 'phone', 'email', 'opening_hours')}),
        ('Social', {'fields': ('facebook_url', 'instagram_url')}),
        ('Management', {'fields': ('manager',)}),
    )

    def image_preview(self, obj):
        return _thumb(obj.main_image)

    image_preview.short_description = "Image"

    def has_add_permission(self, request):
        # New chapters are created nationally; branch admins edit their own.
        return user_is_national_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return user_is_national_admin(request.user)

    def get_readonly_fields(self, request, obj=None):
        if user_is_national_admin(request.user):
            return ()
        return ('slug', 'branch_type', 'parent', 'is_active', 'in_about_menu', 'display_order', 'manager')


@admin.register(BranchTeam)
class BranchTeamAdmin(BranchScopedAdmin):
    list_display = ('member_name', 'designation', 'member_type', 'term', 'branch', 'member_image_preview')
    list_filter = ('member_type', 'branch')
    search_fields = ('member_name', 'designation')

    def member_image_preview(self, obj):
        return _thumb(obj.member_image)

    member_image_preview.short_description = "Image"


@admin.register(BranchGalleryImage)
class BranchGalleryImageAdmin(BranchScopedAdmin):
    list_display = ('branch', 'caption', 'display_order', 'image_preview')
    list_filter = ('branch',)

    def image_preview(self, obj):
        return _thumb(obj.image)

    image_preview.short_description = "Image"


class ProgramImageInline(admin.TabularInline):
    model = ProgramImage
    extra = 1


@admin.register(Program)
class ProgramAdmin(BranchScopedAdmin):
    list_display = ('title', 'branch', 'program_date', 'coordinator_name', 'image_tag')
    search_fields = ('title', 'coordinator_name')
    list_filter = ('branch', 'program_date')
    date_hierarchy = 'program_date'
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'program_date', 'coordinator_name', 'image', 'branch')
        }),
    )
    inlines = [ProgramImageInline]

    def image_tag(self, obj):
        return _thumb(obj.image, 80)

    image_tag.short_description = "Image"


@admin.register(ProgramImage)
class ProgramImageAdmin(BranchScopedAdmin):
    branch_lookup = "program__branch__branch_id__in"
    list_display = ('program', 'image', 'caption')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        ids = admin_branch_ids(request.user)
        if db_field.name == "program" and ids is not None:
            kwargs["queryset"] = Program.objects.filter(branch__branch_id__in=ids)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    search_fields = ('program__title', 'caption')
