from django.db import models

class ElectionCandidate(models.Model):
    POSITION_CHOICES = [
        ('President', 'President'),
        ('Senior Vice-President', 'Senior Vice-President'),
        ('Vice-President', 'Vice-President'),
        ('Secretary General', 'Secretary General'),
        ('Treasurer', 'Treasurer'),
        ('Director', 'Director'),
    ]

    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    date_of_birth = models.DateField()  # New field for DOB
    position = models.CharField(max_length=50, choices=POSITION_CHOICES, default='choose')
    past_position = models.TextField()  # Fixed field name
    profile_picture = models.ImageField(upload_to='candidate_profiles/', blank=True, null=True)
    citizenship_document = models.FileField(upload_to='citizenship_documents/', blank=False, null=False)
    payment_screenshot = models.ImageField(upload_to='payment_screenshots/', blank=False, null=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.position})"
