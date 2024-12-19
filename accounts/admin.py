from django.contrib import admin
from .models import ElectionCandidate

class ElectionCandidateAdmin(admin.ModelAdmin):
    # Make fields read-only in the admin interface
    readonly_fields = (
        'full_name', 'email', 'phone_number', 'address', 'date_of_birth',
        'position', 'past_position', 'profile_picture', 'citizenship_document',
        'payment_screenshot', 'submitted_at'
    )

    # Display these fields in the list view of the admin interface
    list_display = (
        'full_name', 'email', 'position', 'submitted_at',
        'phone_number', 'date_of_birth', 'address'
    )

    # Optional: Disable the "add" and "delete" actions for the model
    def has_add_permission(self, request):
        return False  # Disable adding new candidates

    def has_change_permission(self, request, obj=None):
        return False  # Disable changing candidate details

admin.site.register(ElectionCandidate, ElectionCandidateAdmin)
