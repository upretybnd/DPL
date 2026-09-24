from django import forms
from django.contrib.auth import get_user_model

from accounts.forms import IMAGE_EXTENSIONS, validate_upload
from reports.models import BranchRole
from .models import BranchGalleryImage, BranchTeam, ParentBranch, Program

User = get_user_model()


class ImageCheckMixin:
    """Applies the shared image type/size checks to the named image fields."""

    image_fields = ()

    def clean(self):
        cleaned = super().clean()
        for name in self.image_fields:
            upload = self.files.get(name)
            if upload:
                try:
                    validate_upload(upload, IMAGE_EXTENSIONS)
                except forms.ValidationError as error:
                    self.add_error(name, error)
        return cleaned


class BranchProfileForm(ImageCheckMixin, forms.ModelForm):
    """What a Branch Admin can edit about their own branch."""

    image_fields = ("main_image",)

    class Meta:
        model = ParentBranch
        fields = [
            "name", "tagline", "description", "main_image", "established_date",
            "address", "district", "province", "map_url", "phone", "email", "opening_hours",
            "facebook_url", "instagram_url",
        ]
        widgets = {
            "established_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={"rows": 6}),
        }


class BranchCreateForm(BranchProfileForm):
    """National admins also choose the type, parent, visibility and menu placement."""

    class Meta(BranchProfileForm.Meta):
        fields = ["name", "branch_type", "parent", "is_active", "in_about_menu", "display_order"] + BranchProfileForm.Meta.fields[1:]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = ParentBranch.objects.filter(branch_type=ParentBranch.TYPE_CHAPTER)
        self.fields["parent"].required = False


class TeamMemberForm(ImageCheckMixin, forms.ModelForm):
    image_fields = ("member_image",)

    class Meta:
        model = BranchTeam
        fields = ["member_name", "designation", "member_type", "term", "bio", "member_image", "display_order"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}


class GalleryUploadForm(ImageCheckMixin, forms.ModelForm):
    image_fields = ("image",)

    class Meta:
        model = BranchGalleryImage
        fields = ["image", "caption"]


class ProgramForm(ImageCheckMixin, forms.ModelForm):
    image_fields = ("image",)

    class Meta:
        model = Program
        fields = ["title", "program_date", "coordinator_name", "description", "image"]
        widgets = {
            "program_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={"rows": 6}),
        }


class MemberAddForm(forms.Form):
    email = forms.EmailField(help_text="The person must already have a DPL account (they can sign up on the website).")
    role = forms.ChoiceField()

    def __init__(self, *args, role_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = role_choices

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is None:
            raise forms.ValidationError("No active account uses this email. Ask them to sign up and verify their email first.")
        self.user = user
        return email


class NationalAdminForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        user = User.objects.filter(email__iexact=self.cleaned_data["email"].strip(), is_active=True).first()
        if user is None:
            raise forms.ValidationError("No active account uses this email.")
        self.user = user
        return self.cleaned_data["email"]


ROLE_LABELS = dict(BranchRole.ROLE_CHOICES)
