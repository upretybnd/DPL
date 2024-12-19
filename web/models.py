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

