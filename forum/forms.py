from django import forms
from accounts.forms import IMAGE_EXTENSIONS, validate_upload
from .models import Thread, Reply, UserProfile


class ThreadForm(forms.ModelForm):
    class Meta:
        model = Thread
        fields = ['title', 'content', 'category']
        widgets = {
            'category': forms.Select(),  # This will display categories in a dropdown
        }


class ReplyForm(forms.ModelForm):
    class Meta:
        model = Reply
        fields = ['content']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['full_name','bio', 'profile_picture', 'gender', 'address', 'wall']

    def clean_profile_picture(self):
        return validate_upload(self.cleaned_data.get('profile_picture'), IMAGE_EXTENSIONS)
