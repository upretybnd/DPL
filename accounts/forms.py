from django import forms
from accounts.models import ElectionCandidate

class CandidacyForm(forms.ModelForm):
    class Meta:
        model = ElectionCandidate
        fields = [
            'full_name',
            'email',
            'phone_number',
            'address',
            'date_of_birth',
            'position',
            'past_position',
            'profile_picture',
            'citizenship_document',
            'payment_screenshot',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your full name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your phone number'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Enter your address'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'position': forms.Select(attrs={'class': 'form-control'}),
            'past_position': forms.Textarea(attrs={'rows': 5, 'class': 'form-control', 'placeholder': 'Include details of past positions'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'citizenship_document': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'payment_screenshot': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
