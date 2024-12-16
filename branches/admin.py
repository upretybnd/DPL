from django.contrib import admin
from django.utils.html import format_html, mark_safe
from .models import ParentBranch, BranchTeam, Program, ProgramImage


class BranchTeamInline(admin.TabularInline):
    model = BranchTeam  # Model to link (BranchTeam)
    extra = 1  # Number of extra blank forms for inline editing
    fields = ('member_name', 'designation', 'member_image')  # You can define fields explicitly if needed


class ParentBranchAdmin(admin.ModelAdmin):
    list_display = ('branch_id', 'name', 'description', 'manager')  # Display key fields
    search_fields = ('name',)  # Enable search by branch name
    list_filter = ('name',)  # Add filter options by branch name

    # Inline editing for BranchTeam (inside ParentBranch admin)
    inlines = [BranchTeamInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Allow superusers to see all branches
        if request.user.is_superuser:
            return qs
        # Restrict other users to their assigned branches
        return qs.filter(manager=request.user)


class BranchTeamAdmin(admin.ModelAdmin):
    list_display = ('branch', 'member_name', 'designation', 'member_image_preview')

    def member_image_preview(self, obj):
        if obj.member_image:
            return format_html(f'<img src="{obj.member_image.url}" style="width: 50px; height: 50px;" />')
        return "No Image"

    member_image_preview.short_description = "Image"


# Inline model for ProgramImage
class ProgramImageInline(admin.TabularInline):
    model = ProgramImage
    extra = 1  # Allows adding one additional image by default


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('title', 'branch', 'program_date', 'coordinator_name', 'image_tag')
    search_fields = ('title', 'coordinator_name')
    list_filter = ('branch', 'program_date')

    # Customize the fields shown in the ProgramAdmin form
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'program_date', 'coordinator_name', 'image', 'branch')
        }),
    )

    # Add the ProgramImage inline for related images
    inlines = [ProgramImageInline]

    # Display the main image for Program
    def image_tag(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="100" />')
        return "No image"

    image_tag.allow_tags = True  # Allow HTML in this field


@admin.register(ProgramImage)
class ProgramImageAdmin(admin.ModelAdmin):
    list_display = ('program', 'image', 'caption')
    search_fields = ('program__title', 'caption')


# Registering models and admin configurations
admin.site.register(ParentBranch, ParentBranchAdmin)
admin.site.register(BranchTeam, BranchTeamAdmin)
