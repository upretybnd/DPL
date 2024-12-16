from django import forms
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

    def clean_wall(self):
        # You can add validation for the wall if necessary
        return self.cleaned_data.get('wall')

    def clean_address(self):
        # You can add validation for the address if necessary
        return self.cleaned_data.get('address')
