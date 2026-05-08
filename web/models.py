from django.utils import timezone
from django.db import models

# Define a function to return the default value for the 'role' field
def get_default_role():
    return timezone.now().strftime('%Y-%m-%d %H:%M:%S')  # Format the current time as a string

class Carousel(models.Model):
    title = models.CharField(max_length=200)
    program_organized_by = models.CharField(max_length=200)
    image = models.ImageField(upload_to='banner_img/',blank=False, null=False)

    def __str__(self):
        return self.title


class HomePageMedia(models.Model):
    IMAGE_KEY_CHOICES = [
        ("about_left", "About Left Image"),
        ("about_right", "About Right Image"),
        ("feature_main", "Feature Main Image"),
    ]

    key = models.CharField(max_length=50, choices=IMAGE_KEY_CHOICES, unique=True)
    image = models.ImageField(upload_to="homepage/")
    alt_text = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.get_key_display()
