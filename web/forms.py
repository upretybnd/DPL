from django import forms

from accounts.forms import IMAGE_EXTENSIONS, validate_upload
from .models import ContactMessage, Donation


class HoneypotMixin(forms.Form):
    # Hidden from people with CSS; bots that fill every field get rejected.
    website = forms.CharField(required=False)

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""


class ContactForm(HoneypotMixin, forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]


class NewsletterForm(HoneypotMixin):
    email = forms.EmailField()


class DonationForm(HoneypotMixin, forms.ModelForm):
    class Meta:
        model = Donation
        fields = ["full_name", "email", "phone", "amount", "payment_method", "message", "payment_proof"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["payment_method"].choices = [("", "Choose how you paid")] + Donation.METHOD_CHOICES

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Please enter an amount greater than zero.")
        return amount

    def clean_payment_proof(self):
        return validate_upload(self.cleaned_data.get("payment_proof"), IMAGE_EXTENSIONS)
